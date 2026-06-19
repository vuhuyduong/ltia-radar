import asyncio
import logging
import os
import sys
from bson import ObjectId

# Add app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.mongodb import MongoDB
from app.infrastructure.database.repositories import ProcessedDataRepository, RawDataRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

async def migrate_publish_time():
    logger.info("Connecting to MongoDB...")
    await MongoDB.connect()
    
    processed_repo = ProcessedDataRepository()
    raw_repo = RawDataRepository()
    
    logger.info("Fetching processed documents from 'processed_data'...")
    cursor = processed_repo.collection.find({})
    processed_docs = [doc async for doc in cursor]
    logger.info(f"Found {len(processed_docs)} processed documents in DB.")
    
    updated_count = 0
    skipped_count = 0
    
    for doc in processed_docs:
        doc_id = doc["_id"]
        title = doc.get("title", "")
        raw_id = doc.get("raw_data_id")
        
        publish_time = None
        if raw_id:
            try:
                raw_doc = await raw_repo.collection.find_one({"_id": ObjectId(raw_id)})
                if raw_doc:
                    publish_time = raw_doc.get("publish_time")
            except Exception as e:
                logger.warning(f"Failed to find raw document for id {raw_id}: {e}")
        
        # If no publish_time in raw_doc, fallback to processed_time or datetime.utcnow()
        if not publish_time:
            publish_time = doc.get("processed_time") or doc.get("crawl_time")
            logger.info(f"-> Title: '{title[:40]}' - No publish_time in raw_data. Fallback to: {publish_time}")
        
        if publish_time:
            await processed_repo.collection.update_one(
                {"_id": doc_id},
                {"$set": {"publish_time": publish_time}}
            )
            logger.info(f"-> Updated '{title[:40]}' with publish_time: {publish_time}")
            updated_count += 1
        else:
            logger.warning(f"-> Skipped '{title[:40]}' (no timestamp found at all)")
            skipped_count += 1
            
    logger.info(f"Completed! Updated {updated_count} documents. Skipped {skipped_count}.")
    await MongoDB.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_publish_time())
