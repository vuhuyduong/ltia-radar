import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Ensure backend directory is in path
sys.path.append(".")

from app.config import settings
from app.domain.utils.citation_filter import filter_outlier_citations


async def main():
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    col = db.processed_data

    # Fetch all processed articles (non-irrelevant ones)
    docs = await col.find({"is_relevant": {"$ne": False}}).to_list(length=None)
    print(f"Found {len(docs)} relevant processed articles.")

    cleaned_count = 0
    total_removed_citations = 0

    for doc in docs:
        citations = doc.get("citations", [])
        if not citations:
            continue

        # Save copy of source URLs to check if changes occur
        orig_urls = [c.get("source_url") for c in citations]

        # Run filtering logic
        filtered_citations = filter_outlier_citations(
            citations=citations,
            ref_time=doc.get("publish_time"),
            primary_source_url=doc.get("source_url")
        )

        filtered_urls = [c.get("source_url") for c in filtered_citations]

        # If any citations were removed
        if len(filtered_urls) < len(orig_urls):
            removed = [u for u in orig_urls if u not in filtered_urls]
            print(f"\nCleaning article ID: {doc['_id']} | Title: '{doc.get('title')}'")
            print(f"Reference publish time: {doc.get('publish_time')}")
            print(f"Original citations count: {len(orig_urls)} -> Filtered: {len(filtered_urls)}")
            print(f"Removed citations:")
            for c in citations:
                if c.get("source_url") in removed:
                    print(f"  - [{c.get('publish_time')}] {c.get('title')} ({c.get('source_url')})")
            
            # Update database
            await col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"citations": filtered_citations}}
            )
            cleaned_count += 1
            total_removed_citations += len(removed)

    print("\n--------------------------------------------------")
    print(f"Done! Cleaned {cleaned_count} articles, removing {total_removed_citations} outlier citations.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
