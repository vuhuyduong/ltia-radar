import asyncio
import logging
import os
import sys
from bson import ObjectId

# Add app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.mongodb import MongoDB
from app.infrastructure.llm.gemini import GeminiImplementation
from app.infrastructure.database.repositories import ProcessedDataRepository, RawDataRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

async def reclassify_all():
    logger.info("Connecting to MongoDB...")
    await MongoDB.connect()
    
    processed_repo = ProcessedDataRepository()
    raw_repo = RawDataRepository()
    llm = GeminiImplementation()
    
    logger.info("Fetching processed documents from 'processed_data'...")
    cursor = processed_repo.collection.find({})
    processed_docs = [doc async for doc in cursor]
    logger.info(f"Found {len(processed_docs)} processed documents in DB.")
    
    # Prepare article data for batching
    articles_to_process = []
    for doc in processed_docs:
        title = doc.get("title", "")
        raw_id = doc.get("raw_data_id")
        
        raw_doc = None
        if raw_id:
            try:
                raw_doc = await raw_repo.collection.find_one({"_id": ObjectId(raw_id)})
            except Exception as e:
                logger.warning(f"Failed to find raw document for id {raw_id}: {e}")
                
        raw_text = raw_doc.get("raw_text", "") if raw_doc else ""
        if not raw_text:
            raw_text = doc.get("executive_summary", "")
            
        articles_to_process.append({
            "doc_id": doc["_id"],
            "title": title,
            "raw_text": raw_text
        })
        
    updated_count = 0
    irrelevant_count = 0
    batch_size = 4
    
    # Process in batches of 4
    for i in range(0, len(articles_to_process), batch_size):
        batch = articles_to_process[i : i + batch_size]
        logger.info(f"🧠 Processing batch of {len(batch)} articles (index {i} to {i + len(batch)})")
        
        batch_input = [
            {
                "id": str(art["doc_id"]),
                "title": art["title"],
                "raw_text": art["raw_text"]
            }
            for art in batch
        ]
        
        try:
            insights_list = await llm.extract_insights_batch(batch_input)
            
            for idx, insight in enumerate(insights_list):
                art = batch[idx]
                is_relevant = insight.get("is_relevant", True)
                logger.info(f"-> Title: '{art['title'][:50]}' | Relevant: {is_relevant}")
                
                await processed_repo.collection.update_one(
                    {"_id": art["doc_id"]},
                    {"$set": {"is_relevant": is_relevant}}
                )
                updated_count += 1
                if not is_relevant:
                    irrelevant_count += 1
                    
        except Exception as e:
            logger.error(f"Batch processing failed: {e}. Retrying one by one with delays...")
            for art in batch:
                try:
                    await asyncio.sleep(15) # Wait 15s before call to respect 5 RPM
                    insight = await llm.extract_insight(raw_text=art["raw_text"], title=art["title"])
                    is_relevant = insight.get("is_relevant", True)
                    logger.info(f"-> [Singular] Title: '{art['title'][:50]}' | Relevant: {is_relevant}")
                    
                    await processed_repo.collection.update_one(
                        {"_id": art["doc_id"]},
                        {"$set": {"is_relevant": is_relevant}}
                    )
                    updated_count += 1
                    if not is_relevant:
                        irrelevant_count += 1
                except Exception as ex:
                    logger.error(f"Singular fallback failed for '{art['title'][:50]}': {ex}")
                    
        # Sleep for 15 seconds between batches to avoid 5 RPM rate limit
        if i + batch_size < len(articles_to_process):
            logger.info("⏳ Sleeping 15 seconds to respect rate limits...")
            await asyncio.sleep(15)
            
    logger.info(f"Completed! Re-evaluated {updated_count} documents. Marked {irrelevant_count} as IRRELEVANT.")
    await MongoDB.disconnect()

if __name__ == "__main__":
    asyncio.run(reclassify_all())
