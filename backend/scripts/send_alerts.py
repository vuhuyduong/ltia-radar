#!/usr/bin/env python3
"""
Trigger Telegram alerts for existing HIGH/CRITICAL articles in Atlas.
This simulates the alert matching that happens during crawling.
"""
import asyncio
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)
sys.path.insert(0, "/workspace")

from motor.motor_asyncio import AsyncIOMotorClient
from app.infrastructure.alerting.telegram import TelegramAlertService
from app.domain.entities.processed_data import ProcessedData
from app.domain.entities.alert_rule import AlertRule
from app.config import settings

ATLAS_URI = "mongodb+srv://ltia-admin:%40zUHBhwv5vfiM5j@ltia-radar.h7bibjh.mongodb.net/?appName=ltia-radar"

# Borrowing the match logic from crawl_news.py
def _matches_rule(processed: ProcessedData, rule_doc: dict) -> bool:
    conditions = rule_doc.get("condition_query", {})
    if not conditions:
        return False

    for field, expected_value in conditions.items():
        actual_value = getattr(processed, field, None)
        if actual_value is None:
            return False

        if isinstance(actual_value, list):
            if isinstance(expected_value, list):
                if not any(v in actual_value for v in expected_value):
                    return False
            else:
                if expected_value not in actual_value:
                    return False
        else:
            if isinstance(expected_value, list):
                if getattr(actual_value, "value", str(actual_value)) not in [str(x) for x in expected_value]:
                    return False
            else:
                if getattr(actual_value, "value", str(actual_value)) != str(expected_value):
                    return False
    return True

async def main():
    print(f"Connecting to Atlas...")
    client = AsyncIOMotorClient(ATLAS_URI)
    db = client["ltia_radar"]

    # 1. Fetch active alert rules
    rules_docs = await db.alert_rules.find({"is_active": True}).to_list(length=None)
    print(f"Found {len(rules_docs)} active alert rules")

    # 2. Fetch all relevant articles
    articles_docs = await db.processed_data.find({"is_relevant": True}).to_list(length=None)
    print(f"Found {len(articles_docs)} relevant articles in DB")

    telegram = TelegramAlertService()
    
    # Track sent to avoid duplicates
    sent_ids = set()

    for a_doc in articles_docs:
        a_doc["id"] = str(a_doc.pop("_id"))
        processed = ProcessedData(**a_doc)

        for r_doc in rules_docs:
            if _matches_rule(processed, r_doc):
                if processed.id not in sent_ids:
                    print(f"Matched rule '{r_doc.get('rule_name')}': {processed.title}")
                    r_copy = r_doc.copy()
                    r_copy["id"] = str(r_copy.pop("_id"))
                    rule = AlertRule(**r_copy)
                    success = await telegram.send_alert(processed, rule)
                    if success:
                        print("  ✅ Telegram sent!")
                        sent_ids.add(processed.id)
                    else:
                        print("  ❌ Failed to send")
                    await asyncio.sleep(1) # rate limiting for TG

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
