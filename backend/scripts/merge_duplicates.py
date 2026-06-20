import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from difflib import SequenceMatcher

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ltia-admin:%40zUHBhwv5vfiM5j@ltia-radar.h7bibjh.mongodb.net/?appName=ltia-radar")
    db = client.ltia_radar
    col = db.processed_data

    docs = await col.find({"is_relevant": {"$ne": False}}).to_list(length=None)
    
    merged_count = 0
    to_delete = []
    clusters = []
    
    for doc in docs:
        found = False
        summary = doc.get("executive_summary", "")
        for cluster in clusters:
            c_summary = cluster.get("executive_summary", "")
            if summary and c_summary and SequenceMatcher(None, summary.lower(), c_summary.lower()).ratio() >= 0.85:
                found = True
                to_delete.append(doc["_id"])
                # Merge logic
                existing_c = cluster.get("citations", [])
                if doc.get("source_url") and not any(c.get("source_url") == doc.get("source_url") for c in existing_c):
                    existing_c.append({
                        "title": doc.get("title"),
                        "source_url": doc.get("source_url"),
                        "domain": doc.get("domain", ""),
                        "publish_time": doc.get("publish_time") or doc.get("processed_time")
                    })
                cluster["citations"] = existing_c
                merged_count += 1
                break
        if not found:
            # Ensure the original is added to citations if not already
            existing_c = doc.get("citations", [])
            if doc.get("source_url") and not any(c.get("source_url") == doc.get("source_url") for c in existing_c):
                existing_c.append({
                    "title": doc.get("title"),
                    "source_url": doc.get("source_url"),
                    "domain": doc.get("domain", ""),
                    "publish_time": doc.get("publish_time") or doc.get("processed_time")
                })
            doc["citations"] = existing_c
            clusters.append(doc)
            
    print(f"Merged {merged_count}")
    if merged_count > 0:
        for cluster in clusters:
            if "citations" in cluster:
                await col.update_one({"_id": cluster["_id"]}, {"$set": {"citations": cluster["citations"]}})
        await col.delete_many({"_id": {"$in": to_delete}})
        print(f"✅ Deleted {len(to_delete)}")
    client.close()

asyncio.run(main())
