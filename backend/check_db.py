import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add workspace path to sys.path
sys.path.append("/workspace")

from app.config import settings

async def main():
    print(f"Connecting to MongoDB at: {settings.mongodb_uri}")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]

    for collection_name in ["sources", "keywords", "raw_data", "processed_data", "alert_rules"]:
        count = await db[collection_name].count_documents({})
        print(f"Collection '{collection_name}': {count} documents")

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
