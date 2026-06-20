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

# Default sources list (32 items)
DEFAULT_SOURCES = [
    {"name": "VnExpress - Thời sự", "url": "https://vnexpress.net/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VnExpress - Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "VnExpress - Pháp luật", "url": "https://vnexpress.net/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VnExpress - Khoa học", "url": "https://vnexpress.net/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thời sự", "url": "https://tuoitre.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Pháp luật", "url": "https://tuoitre.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Kinh doanh", "url": "https://tuoitre.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Xe", "url": "https://tuoitre.vn/rss/xe.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thời sự", "url": "https://thanhnien.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Kinh tế", "url": "https://thanhnien.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Pháp luật", "url": "https://thanhnien.vn/rss/thoi-su/phap-luat.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Thời sự", "url": "https://vietnamnet.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Kinh doanh", "url": "https://vietnamnet.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Bất động sản", "url": "https://vietnamnet.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Pháp luật", "url": "https://vietnamnet.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Thời sự", "url": "https://laodong.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Kinh tế", "url": "https://laodong.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Pháp luật", "url": "https://laodong.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Dân trí - Xã hội", "url": "https://dantri.com.vn/rss/xa-hoi.rss", "source_type": "RSS"},
    {"name": "Dân trí - Kinh doanh", "url": "https://dantri.com.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Dân trí - Pháp luật", "url": "https://dantri.com.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VTV - Xã hội", "url": "https://vtv.vn/rss/xa-hoi.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thời sự", "url": "https://nld.com.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Xã hội", "url": "https://nhandan.vn/rss/xa-hoi-582.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Kinh tế", "url": "https://nhandan.vn/rss/kinh-te-515.rss", "source_type": "RSS"},
    {"name": "VOV - Xã hội", "url": "https://vov.vn/rss/xa-hoi-215.rss", "source_type": "RSS"},
    {"name": "VOV - Kinh tế", "url": "https://vov.vn/rss/kinh-te-212.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Thời sự", "url": "https://baodautu.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Bất động sản", "url": "https://baodautu.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VnExpress Tag - Sân bay Long Thành", "url": "https://vnexpress.net/tag/san-bay-long-thanh-216912", "source_type": "WEB"},
    {"name": "Tuổi Trẻ Chủ đề - Sân bay Long Thành", "url": "https://tuoitre.vn/chu-de/san-bay-long-thanh.html", "source_type": "WEB"},
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

# Default LLM Configs
DEFAULT_LLM_CONFIGS = [
    {
        "provider": "Google Gemini",
        "model_name": "gemini-3.5-flash",
        "api_key": "",  # Set via UI or GEMINI_API_KEY env var after deploy
        "is_active": True,
        "is_default": True,
        "description": "Google Gemini 3.5 Flash"
    },
    {
        "provider": "Google Gemini",
        "model_name": "gemini-3-flash-preview",
        "api_key": "",  # Set via UI or GEMINI_API_KEY env var after deploy
        "is_active": False,
        "is_default": False,
        "description": "Google Gemini 3.0 Flash (Preview)"
    },
    {
        "provider": "groq",
        "model_name": "llama-3.3-70b-versatile",
        "api_key": "",  # Set via UI or ENV after deploy
        "is_active": True,
        "is_default": False,
        "description": "Groq Llama 3.3 70B Versatile"
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

    # 4. Seed LLM Configs
    llm_configs_col = db.llm_configs
    print(f"Checking {len(DEFAULT_LLM_CONFIGS)} default LLM configurations...")
    for conf in DEFAULT_LLM_CONFIGS:
        existing = await llm_configs_col.find_one({"model_name": conf["model_name"]})
        if not existing:
            doc = {
                "provider": conf["provider"],
                "model_name": conf["model_name"],
                "api_key": conf["api_key"],
                "is_active": conf["is_active"],
                "is_default": conf["is_default"],
                "description": conf["description"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await llm_configs_col.insert_one(doc)
            print(f"✅ LLM Config seeded: {conf['model_name']}")
        else:
            await llm_configs_col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"is_default": conf["is_default"]}}
            )
            print(f"ℹ️ LLM Config updated (is_default={conf['is_default']}): {conf['model_name']}")

    # 5. Seed / Sync LLM Prompts (always upsert to keep in sync with gemini.py)
    llm_prompts_col = db.llm_prompts
    from app.infrastructure.llm.gemini import SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT
    existing_prompt = await llm_prompts_col.find_one({"is_active": True})
    if existing_prompt:
        await llm_prompts_col.update_one(
            {"_id": existing_prompt["_id"]},
            {
                "$set": {
                    "name": "Prompt CRAFT v2 (Khuyên dùng)",
                    "system_prompt": SYSTEM_PROMPT,
                    "batch_system_prompt": BATCH_SYSTEM_PROMPT,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        print("✅ LLM Prompt synced (upsert) with latest from gemini.py")
    else:
        default_prompt_doc = {
            "name": "Prompt CRAFT v2 (Khuyên dùng)",
            "system_prompt": SYSTEM_PROMPT,
            "batch_system_prompt": BATCH_SYSTEM_PROMPT,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await llm_prompts_col.insert_one(default_prompt_doc)
        print("✅ Default LLM prompt seeded successfully!")


    # Show final counts
    k_cnt = await keywords_col.count_documents({})
    s_cnt = await sources_col.count_documents({})
    r_cnt = await alert_rules_col.count_documents({})
    l_cnt = await llm_configs_col.count_documents({})
    p_cnt = await llm_prompts_col.count_documents({})
    print(f"Final DB State: {k_cnt} keywords, {s_cnt} sources, {r_cnt} alert rules, {l_cnt} LLM configs, {p_cnt} LLM prompts.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

