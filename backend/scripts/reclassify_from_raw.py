#!/usr/bin/env python3
"""
Reclassify existing raw_data in Atlas using the currently active prompt and model.
It deletes all processed_data first!

Run inside Docker container:
  docker compose exec backend python scripts/reclassify_from_raw.py
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
logger = logging.getLogger("reclassify_raw")
logging.getLogger("httpx").setLevel(logging.WARNING)

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.infrastructure.llm.gemini import GeminiImplementation
from app.domain.entities.processed_data import ProcessedData
from app.domain.utils.domain_mapper import get_friendly_domain


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


async def main():
    mongodb_uri = os.environ.get("MONGODB_ATLAS_URI") or getattr(settings, "mongodb_uri", None)
    if not mongodb_uri:
        logger.error("No MongoDB URI found.")
        sys.exit(1)
        
    from app.infrastructure.database.mongodb import MongoDB
    await MongoDB.connect()
    
    client = MongoDB.client
    db = MongoDB.db

    # Initialize LLM
    llm = GeminiImplementation()

    rate_limiter = _RateLimiter(limit=10)

    # Fetch raw data
    raw_docs = await db.raw_data.find({}).to_list(length=None)
    logger.info(f"📋 Found {len(raw_docs)} raw articles to reclassify.")

    if not raw_docs:
        logger.info("No raw docs. Exiting.")
        return

    # Delete processed_data
    logger.info("🗑️ Deleting all existing processed_data...")
    await db.processed_data.delete_many({})

    stats = {"inserted": 0, "errors": 0, "relevant_now": 0, "irrelevant_now": 0}
    start = datetime.utcnow()

    # Build batches
    batch_size = 50
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0

    for doc in raw_docs:
        raw_text = doc.get("raw_text", "") or ""
        content_len = len(raw_text)
        if len(current) >= batch_size or (current_chars + content_len > 300_000 and current):
            batches.append(current)
            current = []
            current_chars = 0
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
                "raw_text": doc.get("raw_text", ""),
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
                raw_doc = batch[idx]
                
                is_rel = cluster.get("is_relevant", False)
                impact = cluster.get("impact_level", "?")
                title = raw_doc.get("title", "")[:60]
                status = "RELEVANT" if is_rel else "irrelevant"
                logger.info(f"  ✓ [{status}|{impact}] {title}")

                if is_rel:
                    stats["relevant_now"] += 1
                else:
                    stats["irrelevant_now"] += 1

                # 2. Insert into processed_data
                citation = {
                    "title": raw_doc.get("title", ""),
                    "source_url": raw_doc.get("source_url", ""),
                    "domain": get_friendly_domain(raw_doc.get("source_url", "")),
                    "publish_time": raw_doc.get("publish_time") or datetime.utcnow(),
                }
                
                # Make sure to not pass unexpected keys to ProcessedData
                # ProcessedData fields:
                # category, sentiment, target_scope, impact_level, key_entities, executive_summary, is_rumor, is_relevant
                # source_url, title, publish_time, citations, raw_data_id
                
                insights = {k: v for k, v in cluster.items() if k not in ["source_indices", "index"]}
                
                try:
                    processed = ProcessedData(
                        raw_data_id=str(raw_doc["_id"]),
                        source_url=raw_doc.get("source_url", ""),
                        title=raw_doc.get("title", ""),
                        publish_time=raw_doc.get("publish_time"),
                        citations=[citation],
                        **insights,
                    )
                    
                    await db.processed_data.insert_one(
                        processed.model_dump(exclude={"id"})
                    )
                    stats["inserted"] += 1
                except Exception as e:
                    logger.error(f"  ✗ Store failed: {e}")
                    stats["errors"] += 1

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info(f"RECLASSIFY FROM RAW COMPLETE — {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"  Inserted   : {stats['inserted']}")
    logger.info(f"  Relevant   : {stats['relevant_now']}")
    logger.info(f"  Irrelevant : {stats['irrelevant_now']}")
    logger.info(f"  Errors     : {stats['errors']}")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
