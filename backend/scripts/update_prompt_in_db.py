#!/usr/bin/env python3
"""
Update LLM Prompt in DB — LTIA Radar
======================================
Sync the new SYSTEM_PROMPT and BATCH_SYSTEM_PROMPT constants from gemini.py
into the active MongoDB prompt document.

Run this inside the Docker container after updating gemini.py:
  docker compose exec backend python scripts/update_prompt_in_db.py
"""

import asyncio
import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)
sys.path.insert(0, "/workspace")

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


async def main():
    # Import after path setup
    from app.config import settings
    from app.infrastructure.llm.gemini import SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT

    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]

    col = db.llm_prompts

    # Find active prompt
    existing = await col.find_one({"is_active": True})

    if existing:
        result = await col.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "system_prompt": SYSTEM_PROMPT,
                    "batch_system_prompt": BATCH_SYSTEM_PROMPT,
                    "updated_at": datetime.utcnow(),
                    "name": "Prompt CRAFT v2 (Khuyên dùng)",
                }
            },
        )
        print(f"✅ Updated active prompt (id={existing['_id']}), matched={result.matched_count}")
    else:
        # Insert new
        doc = {
            "name": "Prompt CRAFT v2 (Khuyên dùng)",
            "system_prompt": SYSTEM_PROMPT,
            "batch_system_prompt": BATCH_SYSTEM_PROMPT,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await col.insert_one(doc)
        print(f"✅ Inserted new prompt (id={result.inserted_id})")

    # Show first 200 chars to confirm
    updated = await col.find_one({"is_active": True})
    print(f"\nPrompt preview (first 200 chars):\n{updated['system_prompt'][:200]}...")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
