#!/usr/bin/env python3
"""
Reclassify raw_data using the currently active prompt and Gemini 3.8 Flash (effort high).
- Incremental by default: only processes raw_data documents not yet present in processed_data
  (neither as raw_data_id nor inside citations.source_url).
- Pass `--reset` to delete all existing processed_data first and reprocess everything.
- Uses clustered storage (one ProcessedData per event cluster with multiple citations)
  and Free Tier KeyPool rate limiting.

Run inside Docker container:
  docker compose exec backend python scripts/reclassify_from_raw.py [--reset]
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime

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

from app.config import settings
from app.domain.entities.processed_data import ProcessedData
from app.domain.utils.domain_mapper import get_friendly_domain
from app.infrastructure.database.mongodb import MongoDB
from app.infrastructure.llm.gemini import GeminiImplementation
from app.infrastructure.llm.quota import QuotaExhausted


def _make_citation(raw_doc: dict) -> dict:
    return {
        "title": raw_doc.get("title", ""),
        "source_url": raw_doc.get("source_url", ""),
        "domain": get_friendly_domain(raw_doc.get("source_url", "")),
        "publish_time": raw_doc.get("publish_time") or datetime.utcnow(),
    }


async def main() -> None:
    reset = "--reset" in sys.argv
    await MongoDB.connect()
    db = MongoDB.db

    if reset:
        logger.info("🗑️ --reset specified: deleting all existing processed_data...")
        await db.processed_data.delete_many({})

    # Find already-processed raw_data_ids and cited URLs so incremental runs resume cleanly
    existing_raw_ids: set[str] = set()
    existing_urls: set[str] = set()
    async for pdoc in db.processed_data.find({}, {"raw_data_id": 1, "source_url": 1, "citations.source_url": 1}):
        if pdoc.get("raw_data_id"):
            existing_raw_ids.add(str(pdoc["raw_data_id"]))
        if pdoc.get("source_url"):
            existing_urls.add(pdoc["source_url"])
        for c in pdoc.get("citations") or []:
            if isinstance(c, dict) and c.get("source_url"):
                existing_urls.add(c["source_url"])

    all_raw = await db.raw_data.find({}).sort("crawl_time", -1).to_list(length=None)
    raw_docs = [
        d
        for d in all_raw
        if str(d["_id"]) not in existing_raw_ids and d.get("source_url") not in existing_urls
    ]
    logger.info(
        f"📋 Found {len(raw_docs)} unprocessed raw articles (out of {len(all_raw)} total)."
    )
    if not raw_docs:
        logger.info("Nothing to process. Exiting.")
        return

    llm = GeminiImplementation()
    stats = {"clusters_inserted": 0, "articles_covered": 0, "relevant_now": 0, "irrelevant_now": 0, "errors": 0}
    start = datetime.utcnow()

    batch_size = settings.llm_batch_max_articles
    max_chars = settings.llm_batch_max_chars
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0

    for doc in raw_docs:
        content_len = min(len(doc.get("raw_text", "") or ""), 3500)
        if len(current) >= batch_size or (current_chars + content_len > max_chars and current):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(doc)
        current_chars += content_len
    if current:
        batches.append(current)

    logger.info(f"📦 {len(batches)} batches (size ≤ {batch_size}, chars ≤ {max_chars})")

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"\n[Batch {batch_num}/{len(batches)}] {len(batch)} articles")

        batch_data = [
            {
                "id": str(doc["_id"]),
                "title": doc.get("title", ""),
                "raw_text": doc.get("raw_text", ""),
                "domain": get_friendly_domain(doc.get("source_url", "")),
                "publish_time": doc["publish_time"].isoformat()
                if isinstance(doc.get("publish_time"), datetime)
                else str(doc.get("publish_time") or ""),
            }
            for doc in batch
        ]

        try:
            results = await llm.extract_insights_batch(batch_data)
        except QuotaExhausted as qe:
            logger.warning(f"⏸️ Quota exhausted at batch {batch_num}: {qe}. Stopping early.")
            stats["errors"] += len(batch)
            break
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            stats["errors"] += len(batch)
            continue

        for cluster in results:
            indices = [i for i in cluster.get("source_indices", []) if isinstance(i, int) and 0 <= i < len(batch)]
            if not indices:
                continue

            primary_doc = batch[indices[0]]
            grouped_docs = [batch[i] for i in indices[1:]]
            citations = [_make_citation(primary_doc)] + [_make_citation(g) for g in grouped_docs]

            is_rel = bool(cluster.get("is_relevant", False))
            impact = cluster.get("impact_level", "?")
            title = primary_doc.get("title", "")[:65]
            status = "RELEVANT" if is_rel else "irrelevant"
            logger.info(f"  ✓ [{status}|{impact}|x{len(indices)}] {title}")

            if is_rel:
                stats["relevant_now"] += 1
            else:
                stats["irrelevant_now"] += 1

            pub_time = primary_doc.get("publish_time")
            if not pub_time:
                for g in grouped_docs:
                    if g.get("publish_time"):
                        pub_time = g.get("publish_time")
                        break
            if not pub_time:
                pub_time = primary_doc.get("crawl_time") or datetime.utcnow()

            insights = {k: v for k, v in cluster.items() if k not in ("source_indices", "index")}
            try:
                processed = ProcessedData(
                    raw_data_id=str(primary_doc["_id"]),
                    source_url=primary_doc.get("source_url", ""),
                    title=primary_doc.get("title", ""),
                    publish_time=pub_time,
                    citations=citations,
                    **insights,
                )
                await db.processed_data.insert_one(processed.model_dump(exclude={"id"}))
                stats["clusters_inserted"] += 1
                stats["articles_covered"] += len(indices)
            except Exception as e:
                logger.error(f"  ✗ Store failed: {e}")
                stats["errors"] += len(indices)

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info(f"RECLASSIFY FROM RAW COMPLETE — {elapsed:.0f}s ({elapsed/60:.1f}min)")
    logger.info(f"  Clusters inserted : {stats['clusters_inserted']} (covering {stats['articles_covered']} raw articles)")
    logger.info(f"  Relevant clusters : {stats['relevant_now']}")
    logger.info(f"  Irrelevant        : {stats['irrelevant_now']}")
    logger.info(f"  Errors            : {stats['errors']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
