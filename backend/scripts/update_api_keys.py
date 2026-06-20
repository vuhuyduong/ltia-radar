#!/usr/bin/env python3
"""Update both Gemini API keys into Atlas llm_configs for rotation."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

ATLAS_URI = "mongodb+srv://ltia-admin:%40zUHBhwv5vfiM5j@ltia-radar.h7bibjh.mongodb.net/?appName=ltia-radar"
DB_NAME = "ltia_radar"

# Both API keys for rotation
API_KEYS = [
    "",
    "",
]

async def main():
    client = AsyncIOMotorClient(ATLAS_URI)
    db = client[DB_NAME]

    col = db.llm_configs

    # Find existing default config
    existing = await col.find_one({"is_default": True})

    if existing:
        old_keys = existing.get("api_keys", [])
        result = await col.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "api_keys": API_KEYS,
                "model_name": "gemini-2.5-flash-preview-05-20",
                "rate_limit_per_minute": 10,
                "updated_at": datetime.utcnow(),
            }}
        )
        print(f"✅ Updated LLM config")
        print(f"   Old keys count: {len(old_keys)}")
        print(f"   New keys: {len(API_KEYS)} keys configured for rotation")
    else:
        await col.insert_one({
            "model_name": "gemini-2.5-flash-preview-05-20",
            "api_keys": API_KEYS,
            "rate_limit_per_minute": 10,
            "is_default": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        print(f"✅ Created new LLM config with {len(API_KEYS)} keys")

    # Verify
    updated = await col.find_one({"is_default": True})
    print(f"\nVerification:")
    print(f"  Model: {updated.get('model_name')}")
    print(f"  Keys: {len(updated.get('api_keys', []))} keys")
    for i, k in enumerate(updated.get('api_keys', [])):
        print(f"    [{i+1}] {k[:20]}...{k[-8:]}")

    client.close()

asyncio.run(main())
