import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

ATLAS_URI = "mongodb+srv://ltia-admin:%40zUHBhwv5vfiM5j@ltia-radar.h7bibjh.mongodb.net/?appName=ltia-radar"

async def check():
    client = AsyncIOMotorClient(ATLAS_URI)
    db = client["ltia_radar"]

    raw = await db.raw_data.count_documents({})
    proc = await db.processed_data.count_documents({})
    relevant = await db.processed_data.count_documents({"is_relevant": True})

    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$publish_time"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    dates = await db.raw_data.aggregate(pipeline).to_list(length=100)

    print(f"raw_data: {raw} | processed: {proc} | relevant: {relevant}")
    print("\nDate distribution in raw_data:")
    for d in dates:
        print(f"  {d['_id']}: {d['count']} articles")

    oldest = await db.raw_data.find_one({}, sort=[("publish_time", 1)])
    newest = await db.raw_data.find_one({}, sort=[("publish_time", -1)])
    if oldest:
        print(f"\nOldest: {oldest.get('publish_time')} — {oldest.get('title', '')[:70]}")
    if newest:
        print(f"Newest: {newest.get('publish_time')} — {newest.get('title', '')[:70]}")

    # Check impact level distribution in processed
    pipeline2 = [
        {"$group": {"_id": "$impact_level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    impacts = await db.processed_data.aggregate(pipeline2).to_list(length=10)
    print("\nImpact level distribution:")
    for i in impacts:
        print(f"  {i['_id']}: {i['count']}")

    client.close()

asyncio.run(check())
