import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add workspace path to sys.path so we can import from app
sys.path.append("/workspace")

from app.config import settings

# Default keywords list (20 items)
DEFAULT_KEYWORDS = [
    "sân bay Long Thành",
    "gói thầu 5.10",
    "gói thầu 4.6",
    "Vietur",
    "bụi đỏ",
    "giải phóng mặt bằng",
    "ACV",
    "nhà ga hành khách",
    "đường băng Long Thành",
    "tái định cư Lộc An",
    "tiến độ Long Thành",
    "thu hồi đất Long Thành",
    "giao thông kết nối Long Thành",
    "đóng điện sân bay Long Thành",
    "gói thầu sân bay",
    "tổng công ty cảng hàng không",
    "khởi công Long Thành",
    "khánh thành Long Thành",
    "đường cất hạ cánh",
    "tháp không lưu Long Thành"
]

# Default sources list (16 items)
DEFAULT_SOURCES = [
    {"name": "VnExpress - Thời sự", "url": "https://vnexpress.net/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VnExpress - Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thời sự", "url": "https://tuoitre.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Pháp luật", "url": "https://tuoitre.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thời sự", "url": "https://thanhnien.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Kinh tế", "url": "https://thanhnien.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Thời sự", "url": "https://vietnamnet.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Kinh doanh", "url": "https://vietnamnet.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Báo Giao thông - Thời sự", "url": "https://www.baogiaothong.vn/rss/thoi-su-2.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Thời sự", "url": "https://laodong.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VTV - Trong nước", "url": "https://vtv.vn/trong-nuoc.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thời sự", "url": "https://nld.com.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VnExpress Tag - Sân bay Long Thành", "url": "https://vnexpress.net/tag/san-bay-long-thanh-216912", "source_type": "WEB"},
    {"name": "Tuổi Trẻ Chủ đề - Sân bay Long Thành", "url": "https://tuoitre.vn/chu-de/san-bay-long-thanh.html", "source_type": "WEB"},
    {"name": "VietnamNet Tag - Sân bay Long Thành", "url": "https://vietnamnet.vn/san-bay-long-thanh-tag8279442006764491745.html", "source_type": "WEB"},
    {"name": "Báo Giao thông - Tìm kiếm Long Thành", "url": "https://www.baogiaothong.vn/tim-kiem.html?q=s%C3%A2n+bay+Long+Th%C3%A0nh", "source_type": "WEB"},
]

# Default Alert Rules
DEFAULT_ALERT_RULES = [
    {
        "rule_name": "Cảnh báo Khủng hoảng Tiến độ/An toàn/Sự cố (Negative & Critical/High)",
        "condition_query": {
            "sentiment": "NEGATIVE",
            "impact_level": ["CRITICAL", "HIGH"]
        },
        "telegram_chat_id": "default_chat_id",
        "is_active": True
    },
    {
        "rule_name": "Cảnh báo Sự cố Nghiêm trọng (Critical)",
        "condition_query": {
            "impact_level": "CRITICAL"
        },
        "telegram_chat_id": "default_chat_id",
        "is_active": True
    }
]

async def main():
    print(f"Connecting to MongoDB at: {settings.mongodb_uri}")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    
    # 1. Seed Keywords
    keywords_col = db.keywords
    existing_kws_count = await keywords_col.count_documents({})
    if existing_kws_count == 0:
        print(f"Seeding {len(DEFAULT_KEYWORDS)} default keywords...")
        keywords_docs = [
            {
                "value": kw,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            } for kw in DEFAULT_KEYWORDS
        ]
        await keywords_col.insert_many(keywords_docs)
        print("✅ Keywords seeded successfully!")
    else:
        print(f"ℹ️ Keywords collection already has {existing_kws_count} items. Skipping seeding.")

    # 2. Seed Sources
    sources_col = db.sources
    existing_sources_count = await sources_col.count_documents({})
    if existing_sources_count == 0:
        print(f"Seeding {len(DEFAULT_SOURCES)} default sources...")
        sources_docs = [
            {
                "name": src["name"],
                "url": src["url"],
                "source_type": src["source_type"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            } for src in DEFAULT_SOURCES
        ]
        await sources_col.insert_many(sources_docs)
        print("✅ Sources seeded successfully!")
    else:
        print(f"ℹ️ Sources collection already has {existing_sources_count} items. Skipping seeding.")

    # 3. Seed Alert Rules
    alert_rules_col = db.alert_rules
    existing_rules_count = await alert_rules_col.count_documents({})
    if existing_rules_count == 0:
        print(f"Seeding {len(DEFAULT_ALERT_RULES)} default alert rules...")
        rules_docs = [
            {
                "rule_name": rule["rule_name"],
                "condition_query": rule["condition_query"],
                "telegram_chat_id": rule["telegram_chat_id"],
                "is_active": rule["is_active"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            } for rule in DEFAULT_ALERT_RULES
        ]
        await alert_rules_col.insert_many(rules_docs)
        print("✅ Alert Rules seeded successfully!")
    else:
        print(f"ℹ️ Alert Rules collection already has {existing_rules_count} items. Skipping seeding.")

    # Show final counts
    k_cnt = await keywords_col.count_documents({})
    s_cnt = await sources_col.count_documents({})
    r_cnt = await alert_rules_col.count_documents({})
    print(f"Final DB State: {k_cnt} keywords, {s_cnt} sources, {r_cnt} alert rules.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
