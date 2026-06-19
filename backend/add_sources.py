import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add workspace path to sys.path so we can import from app
sys.path.append("/workspace")

from app.config import settings

# Default sources list (34 items)
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
    {"name": "Thanh Niên - Pháp luật", "url": "https://thanhnien.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Thời sự", "url": "https://vietnamnet.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Kinh doanh", "url": "https://vietnamnet.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Bất động sản", "url": "https://vietnamnet.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Pháp luật", "url": "https://vietnamnet.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Báo Giao thông - Thời sự", "url": "https://www.baogiaothong.vn/rss/thoi-su-2.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Thời sự", "url": "https://laodong.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Kinh tế", "url": "https://laodong.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Pháp luật", "url": "https://laodong.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Dân trí - Xã hội", "url": "https://dantri.com.vn/rss/xa-hoi.rss", "source_type": "RSS"},
    {"name": "Dân trí - Kinh doanh", "url": "https://dantri.com.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Dân trí - Pháp luật", "url": "https://dantri.com.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VTV - Trong nước", "url": "https://vtv.vn/trong-nuoc.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thời sự", "url": "https://nld.com.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Xã hội", "url": "https://nhandan.vn/rss/xa-hoi-582.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Kinh tế", "url": "https://nhandan.vn/rss/kinh-te-515.rss", "source_type": "RSS"},
    {"name": "VOV - Xã hội", "url": "https://vov.vn/rss/xa-hoi-215.rss", "source_type": "RSS"},
    {"name": "VOV - Kinh tế", "url": "https://vov.vn/rss/kinh-te-212.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Thời sự", "url": "https://baodautu.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Bất động sản", "url": "https://baodautu.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VnExpress Tag - Sân bay Long Thành", "url": "https://vnexpress.net/tag/san-bay-long-thanh-216912", "source_type": "WEB"},
    {"name": "Tuổi Trẻ Chủ đề - Sân bay Long Thành", "url": "https://tuoitre.vn/chu-de/san-bay-long-thanh.html", "source_type": "WEB"},
    {"name": "VietnamNet Tag - Sân bay Long Thành", "url": "https://vietnamnet.vn/san-bay-long-thanh-tag8279442006764491745.html", "source_type": "WEB"},
    {"name": "Báo Giao thông - Tìm kiếm Long Thành", "url": "https://www.baogiaothong.vn/tim-kiem.html?q=s%C3%A2n+bay+Long+Th%C3%A0nh", "source_type": "WEB"},
]

async def main():
    print(f"Connecting to MongoDB at: {settings.mongodb_uri}")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    sources_col = db.sources

    added_count = 0
    skipped_count = 0

    for src in DEFAULT_SOURCES:
        # Check if source URL already exists
        exists = await sources_col.count_documents({"url": src["url"]})
        if exists == 0:
            doc = {
                "name": src["name"],
                "url": src["url"],
                "source_type": src["source_type"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await sources_col.insert_one(doc)
            print(f"➕ Added source: {src['name']} ({src['url']})")
            added_count += 1
        else:
            skipped_count += 1

    print(f"\n✅ Completed adding sources! Added: {added_count}, Skipped (already exist): {skipped_count}.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
