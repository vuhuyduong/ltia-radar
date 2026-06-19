"""
Migration: Add text index on processed_data.title for find_similar_article().

Run once inside the backend container:
    docker compose exec backend python migration_add_title_text_index.py

This enables the two-phase similarity search (MongoDB $text pre-filter → Python
SequenceMatcher on ≤20 candidates) replacing the previous O(N) full-collection scan.
"""

import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration() -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    collection = db.processed_data

    # Check if text index already exists
    existing_indexes = await collection.index_information()
    has_text_index = any(
        "text" in str(info.get("key", {}))
        for info in existing_indexes.values()
    )

    if has_text_index:
        logger.info("✅ Text index on processed_data.title already exists — skipping.")
        client.close()
        return

    logger.info("📦 Creating text index on processed_data.title...")
    await collection.create_index([("title", "text")], name="title_text_idx")
    logger.info("✅ Text index created successfully.")

    # Verify
    indexes = await collection.index_information()
    logger.info(f"Current indexes: {list(indexes.keys())}")
    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
