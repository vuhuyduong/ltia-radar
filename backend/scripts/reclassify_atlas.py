#!/usr/bin/env python3
"""
Reclassify existing processed_data in Atlas with the new CRAFT v2 prompt.

Run inside Docker container:
  docker compose exec backend python scripts/reclassify_atlas.py \
    --mongodb-uri "mongodb+srv://..." \
    --gemini-key "AIzaSy..."

This script:
  1. Fetches all processed_data from Atlas
  2. Re-runs LLM classification on each article using the new prompt
  3. Updates processed_data with new classification results
"""
from __future__ import annotations
import asyncio
import os
import sys
import time
import logging

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)
sys.path.insert(0, "/workspace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("reclassify")
logging.getLogger("httpx").setLevel(logging.WARNING)

import argparse
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient


ATLAS_URI = "mongodb+srv://ltia-admin:%40zUHBhwv5vfiM5j@ltia-radar.h7bibjh.mongodb.net/?appName=ltia-radar"
DB_NAME = "ltia_radar"

CLASSIFICATION_FIELDS = {
    "category", "sentiment", "target_scope", "impact_level",
    "key_entities", "executive_summary", "is_rumor", "is_relevant"
}


class _RateLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._count = 0
        self._window_start = time.monotonic()

    async def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self._window_start
        if elapsed >= 60.0:
            self._count = 0
            self._window_start = now
        if self._count >= self._limit:
            wait = 60.0 - elapsed
            logger.info(f"⏳ Rate limit reached — sleeping {wait:.1f}s")
            await asyncio.sleep(wait)
            self._count = 0
            self._window_start = time.monotonic()
        self._count += 1


async def reclassify(
    mongodb_uri: str,
    db_name: str,
    gemini_key: str,
    batch_size: int,
    dry_run: bool,
    only_relevant: bool,
) -> None:
    from app.infrastructure.llm.gemini import GeminiImplementation, SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT

    client = AsyncIOMotorClient(mongodb_uri)
    db = client[db_name]

    # Fetch all API keys from DB for rotation
    cfg = await db.llm_configs.find_one({"is_default": True})
    db_keys = cfg.get("api_keys", []) if cfg else []

    # Merge: CLI key + DB keys (deduplicated)
    all_keys = [gemini_key] + [k for k in db_keys if k != gemini_key]

    llm = GeminiImplementation()
    llm._cached_keys = all_keys
    llm._cached_model = "gemini-2.5-flash"   # Use working model
    llm._cached_sys_prompt = SYSTEM_PROMPT
    llm._cached_batch_prompt = BATCH_SYSTEM_PROMPT
    logger.info(f"🔑 {len(all_keys)} API key(s) loaded for rotation")
    logger.info(f"🤖 Model: {llm._cached_model}")

    rate_limiter = _RateLimiter(limit=10)

    # Fetch articles to reclassify
    query = {}
    if only_relevant:
        query["is_relevant"] = True

    docs = await db.processed_data.find(query).to_list(length=None)
    logger.info(f"📋 Found {len(docs)} processed articles to reclassify")

    # Also fetch raw_text from raw_data for each
    raw_map: dict[str, str] = {}
    raw_docs = await db.raw_data.find({}, {"url_hash": 1, "raw_text": 1, "title": 1}).to_list(length=None)
    for r in raw_docs:
        raw_id = str(r["_id"])
        raw_map[raw_id] = r.get("raw_text", "") or ""

    stats = {"updated": 0, "errors": 0, "relevant_now": 0, "irrelevant_now": 0}
    start = datetime.utcnow()

    # Build batches
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0

    for doc in docs:
        raw_id = doc.get("raw_data_id", "")
        raw_text = raw_map.get(raw_id, "")
        content_len = len(raw_text)
        if len(current) >= batch_size or (current_chars + content_len > 320_000 and current):
            batches.append(current)
            current = []
            current_chars = 0
        doc["_raw_text"] = raw_text
        current.append(doc)
        current_chars += content_len
    if current:
        batches.append(current)

    logger.info(f"📦 {len(batches)} batches (size ≤ {batch_size})")

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"\n[Batch {batch_num}/{len(batches)}] {len(batch)} articles")
        await rate_limiter.acquire()

        batch_data = [
            {
                "id": str(i),
                "title": doc.get("title", ""),
                "raw_text": doc.get("_raw_text", ""),
            }
            for i, doc in enumerate(batch)
        ]

        try:
            results = await llm.extract_insights_batch(batch_data)
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            stats["errors"] += len(batch)
            continue

        for cluster in results:
            indices = cluster.get("source_indices", [])
            for idx in indices:
                if idx >= len(batch): continue
                doc = batch[idx]
                
                is_rel = cluster.get("is_relevant", False)
                impact = cluster.get("impact_level", "?")
                title = doc.get("title", "")[:60]
                status = "RELEVANT" if is_rel else "irrelevant"
                logger.info(f"  ✓ [{status}|{impact}] {title}")

                if is_rel:
                    stats["relevant_now"] += 1
                else:
                    stats["irrelevant_now"] += 1

                if dry_run:
                    continue

                # Update only classification fields
                update_fields = {k: v for k, v in cluster.items() if k in CLASSIFICATION_FIELDS}
                update_fields["reclassified_at"] = datetime.utcnow()
                try:
                    await db.processed_data.update_one(
                        {"_id": doc["_id"]},
                        {"$set": update_fields},
                    )
                    stats["updated"] += 1
                except Exception as e:
                    logger.error(f"  ✗ Update failed: {e}")
                    stats["errors"] += 1

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info(f"RECLASSIFY COMPLETE — {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"  Updated    : {stats['updated']}")
    logger.info(f"  Relevant   : {stats['relevant_now']}")
    logger.info(f"  Irrelevant : {stats['irrelevant_now']}")
    logger.info(f"  Errors     : {stats['errors']}")
    logger.info("=" * 60)

    client.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reclassify Atlas articles with new CRAFT v2 prompt")
    p.add_argument("--mongodb-uri", default=ATLAS_URI)
    p.add_argument("--db-name", default=DB_NAME)
    p.add_argument("--gemini-key", required=True, help="Valid Gemini API key (AIzaSy...)")
    p.add_argument("--batch-size", type=int, default=80)
    p.add_argument("--only-relevant", action="store_true", help="Only reclassify articles currently marked relevant")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    from app.config import settings  # noqa — just to ensure path is set up

    await reclassify(
        mongodb_uri=args.mongodb_uri,
        db_name=args.db_name,
        gemini_key=args.gemini_key,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        only_relevant=args.only_relevant,
    )


if __name__ == "__main__":
    # Lazy import app modules
    asyncio.run(main())
