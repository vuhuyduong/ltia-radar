import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add workspace path to sys.path so we can import from app
sys.path.append("/workspace")

from app.config import settings

# Default keywords list (updated with trial/start of operation terms)
DEFAULT_KEYWORDS = [
    # ── Từ khóa cũ ──
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
    "tháp không lưu Long Thành",
    
    # ── Chuẩn bị khai thác ──
    "chuẩn bị khai thác sân bay Long Thành",
    "chuẩn bị khai thác Long Thành",
    "phương án khai thác Long Thành",
    "quy trình khai thác Long Thành",
    "kế hoạch vận hành Long Thành",
    "đào tạo vận hành Long Thành",
    "công tác chuẩn bị khai thác",
    "chuyển giao khai thác Long Thành",
    
    # ── Khai thác thử / Bay thử / Nghiệm thu ──
    "khai thác thử sân bay Long Thành",
    "khai thác thử Long Thành",
    "bay thử sân bay Long Thành",
    "bay thử Long Thành",
    "bay hiệu chuẩn Long Thành",
    "vận hành thử Long Thành",
    "chạy thử nhà ga Long Thành",
    "chạy thử sân bay Long Thành",
    "diễn tập khai thác Long Thành",
    "hoạt động thử nghiệm Long Thành",
    "bay kiểm nghiệm Long Thành",
    
    # ── Bắt đầu khai thác / Vận hành thương mại ──
    "khai thác thương mại Long Thành",
    "mở cửa sân bay Long Thành",
    "bắt đầu khai thác Long Thành",
    "cấp phép khai thác Long Thành",
    "khai trương sân bay Long Thành",
    "vận hành thương mại Long Thành",
    "đón chuyến bay đầu tiên Long Thành",
    "chuyến bay đầu tiên sân bay Long Thành",
    "ngày khai thác sân bay Long Thành"
]

# Default sources list (expanded to cover all categories for each source)
DEFAULT_SOURCES = [
    # ── VnExpress ──
    {"name": "VnExpress - Tin mới nhất", "url": "https://vnexpress.net/rss/tin-moi-nhat.rss", "source_type": "RSS"},
    {"name": "VnExpress - Tin nổi bật", "url": "https://vnexpress.net/rss/tin-noi-bat.rss", "source_type": "RSS"},
    {"name": "VnExpress - Thời sự", "url": "https://vnexpress.net/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VnExpress - Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "VnExpress - Pháp luật", "url": "https://vnexpress.net/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VnExpress - Khoa học", "url": "https://vnexpress.net/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "VnExpress - Thế giới", "url": "https://vnexpress.net/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "VnExpress - Giải trí", "url": "https://vnexpress.net/rss/giai-tri.rss", "source_type": "RSS"},
    {"name": "VnExpress - Thể thao", "url": "https://vnexpress.net/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "VnExpress - Giáo dục", "url": "https://vnexpress.net/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "VnExpress - Góc nhìn", "url": "https://vnexpress.net/rss/goc-nhin.rss", "source_type": "RSS"},
    {"name": "VnExpress - Bất động sản", "url": "https://vnexpress.net/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VnExpress - Sức khỏe", "url": "https://vnexpress.net/rss/suc-khoe.rss", "source_type": "RSS"},
    {"name": "VnExpress - Đời sống", "url": "https://vnexpress.net/rss/gia-dinh.rss", "source_type": "RSS"},
    {"name": "VnExpress - Du lịch", "url": "https://vnexpress.net/rss/du-lich.rss", "source_type": "RSS"},
    {"name": "VnExpress - Khoa học công nghệ", "url": "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss", "source_type": "RSS"},
    {"name": "VnExpress - Xe", "url": "https://vnexpress.net/rss/oto-xe-may.rss", "source_type": "RSS"},
    {"name": "VnExpress - Ý kiến", "url": "https://vnexpress.net/rss/y-kien.rss", "source_type": "RSS"},
    {"name": "VnExpress - Tâm sự", "url": "https://vnexpress.net/rss/tam-su.rss", "source_type": "RSS"},
    {"name": "VnExpress - VnE-GO", "url": "https://vnexpress.net/rss/vne-go.rss", "source_type": "RSS"},
    {"name": "VnExpress - Thư giãn", "url": "https://vnexpress.net/rss/thu-gian.rss", "source_type": "RSS"},
    {"name": "VnExpress - Spotlight", "url": "https://vnexpress.net/rss/spotlight.rss", "source_type": "RSS"},
    {"name": "VnExpress - Tin xem nhiều", "url": "https://vnexpress.net/rss/tin-xem-nhieu.rss", "source_type": "RSS"},

    # ── Tuổi Trẻ ──
    {"name": "Tuổi Trẻ - Trang chủ", "url": "https://tuoitre.vn/home.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thời sự", "url": "https://tuoitre.vn/thoi-su.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thế giới", "url": "https://tuoitre.vn/the-gioi.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Pháp luật", "url": "https://tuoitre.vn/phap-luat.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Kinh doanh", "url": "https://tuoitre.vn/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Công nghệ", "url": "https://tuoitre.vn/nhip-song-so.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Xe", "url": "https://tuoitre.vn/xe.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Nhịp sống trẻ", "url": "https://tuoitre.vn/nhip-song-tre.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Văn hóa", "url": "https://tuoitre.vn/van-hoa.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Giải trí", "url": "https://tuoitre.vn/giai-tri.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thể thao", "url": "https://tuoitre.vn/the-thao.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Giáo dục", "url": "https://tuoitre.vn/giao-duc.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Khoa học", "url": "https://tuoitre.vn/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Sức khỏe", "url": "https://tuoitre.vn/suc-khoe.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Giả thật", "url": "https://tuoitre.vn/gia-that.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Thư giãn", "url": "https://tuoitre.vn/thu-gian.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Bạn đọc", "url": "https://tuoitre.vn/ban-doc.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Du lịch", "url": "https://tuoitre.vn/du-lich.rss", "source_type": "RSS"},
    {"name": "Tuổi Trẻ - Video", "url": "https://tuoitre.vn/video.rss", "source_type": "RSS"},

    # ── Thanh Niên ──
    {"name": "Thanh Niên - Trang chủ", "url": "https://thanhnien.vn/rss/home.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thời sự", "url": "https://thanhnien.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Pháp luật", "url": "https://thanhnien.vn/rss/thoi-su/phap-luat.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Dân sinh", "url": "https://thanhnien.vn/rss/thoi-su/dan-sinh.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Lao động - Việc làm", "url": "https://thanhnien.vn/rss/thoi-su/lao-dong-viec-lam.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Chính trị", "url": "https://thanhnien.vn/rss/chinh-tri.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thế giới", "url": "https://thanhnien.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Kinh tế", "url": "https://thanhnien.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Địa ốc", "url": "https://thanhnien.vn/rss/kinh-te/dia-oc.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Đời sống", "url": "https://thanhnien.vn/rss/doi-song.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Sức khỏe", "url": "https://thanhnien.vn/rss/suc-khoe.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Giới trẻ", "url": "https://thanhnien.vn/rss/gioi-tre.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Giáo dục", "url": "https://thanhnien.vn/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Du lịch", "url": "https://thanhnien.vn/rss/du-lich.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Văn hóa", "url": "https://thanhnien.vn/rss/van-hoa.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Giải trí", "url": "https://thanhnien.vn/rss/giai-tri.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thể thao", "url": "https://thanhnien.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Công nghệ", "url": "https://thanhnien.vn/rss/cong-nghe.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Xe", "url": "https://thanhnien.vn/rss/xe.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Thời trang trẻ", "url": "https://thanhnien.vn/rss/thoi-trang-tre.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Bạn đọc", "url": "https://thanhnien.vn/rss/ban-doc.rss", "source_type": "RSS"},
    {"name": "Thanh Niên - Tiêu dùng thông minh", "url": "https://thanhnien.vn/rss/tieu-dung-thong-minh.rss", "source_type": "RSS"},

    # ── VietnamNet ──
    {"name": "VietnamNet - Thời sự", "url": "https://vietnamnet.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Kinh doanh", "url": "https://vietnamnet.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Bất động sản", "url": "https://vietnamnet.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Pháp luật", "url": "https://vietnamnet.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Thế giới", "url": "https://vietnamnet.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Giải trí", "url": "https://vietnamnet.vn/rss/giai-tri.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Thể thao", "url": "https://vietnamnet.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Giáo dục", "url": "https://vietnamnet.vn/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Sức khỏe", "url": "https://vietnamnet.vn/rss/suc-khoe.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Đời sống", "url": "https://vietnamnet.vn/rss/doi-song.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Du lịch", "url": "https://vietnamnet.vn/rss/du-lich.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Khoa học", "url": "https://vietnamnet.vn/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Góc nhìn", "url": "https://vietnamnet.vn/rss/goc-nhin.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Tuần Việt Nam", "url": "https://vietnamnet.vn/rss/tuan-viet-nam.rss", "source_type": "RSS"},
    {"name": "VietnamNet - Bạn đọc", "url": "https://vietnamnet.vn/rss/ban-doc.rss", "source_type": "RSS"},

    # ── Báo Lao động ──
    {"name": "Báo Lao động - Thời sự", "url": "https://laodong.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Kinh tế", "url": "https://laodong.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Pháp luật", "url": "https://laodong.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Thế giới", "url": "https://laodong.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Xã hội", "url": "https://laodong.vn/rss/xa-hoi.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Công đoàn", "url": "https://laodong.vn/rss/cong-doan.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Văn hóa Giải trí", "url": "https://laodong.vn/rss/van-hoa-giai-tri.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Thể thao", "url": "https://laodong.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Tấm lòng vàng", "url": "https://laodong.vn/rss/tam-long-vang.rss", "source_type": "RSS"},
    {"name": "Báo Lao động - Bạn đọc", "url": "https://laodong.vn/rss/ban-doc.rss", "source_type": "RSS"},

    # ── Dân trí ──
    {"name": "Dân trí - Trang chủ", "url": "https://dantri.com.vn/rss/home.rss", "source_type": "RSS"},
    {"name": "Dân trí - Sự kiện", "url": "https://dantri.com.vn/rss/su-kien.rss", "source_type": "RSS"},
    {"name": "Dân trí - Thời sự", "url": "https://dantri.com.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Dân trí - Thế giới", "url": "https://dantri.com.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "Dân trí - Giá vàng", "url": "https://dantri.com.vn/rss/gia-vang.rss", "source_type": "RSS"},
    {"name": "Dân trí - Đời sống", "url": "https://dantri.com.vn/rss/doi-song.rss", "source_type": "RSS"},
    {"name": "Dân trí - Thể thao", "url": "https://dantri.com.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "Dân trí - Lao động - Việc làm", "url": "https://dantri.com.vn/rss/lao-dong-viec-lam.rss", "source_type": "RSS"},
    {"name": "Dân trí - Giáo dục", "url": "https://dantri.com.vn/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "Dân trí - Tấm lòng nhân ái", "url": "https://dantri.com.vn/rss/tam-long-nhan-ai.rss", "source_type": "RSS"},
    {"name": "Dân trí - Kinh doanh", "url": "https://dantri.com.vn/rss/kinh-doanh.rss", "source_type": "RSS"},
    {"name": "Dân trí - Bất động sản", "url": "https://dantri.com.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "Dân trí - Giải trí", "url": "https://dantri.com.vn/rss/giai-tri.rss", "source_type": "RSS"},
    {"name": "Dân trí - Du lịch", "url": "https://dantri.com.vn/rss/du-lich.rss", "source_type": "RSS"},
    {"name": "Dân trí - Pháp luật", "url": "https://dantri.com.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Dân trí - Sức khỏe", "url": "https://dantri.com.vn/rss/suc-khoe.rss", "source_type": "RSS"},
    {"name": "Dân trí - Công nghệ", "url": "https://dantri.com.vn/rss/cong-nghe.rss", "source_type": "RSS"},
    {"name": "Dân trí - Ô tô - Xe máy", "url": "https://dantri.com.vn/rss/o-to-xe-may.rss", "source_type": "RSS"},
    {"name": "Dân trí - Tình yêu - Giới tính", "url": "https://dantri.com.vn/rss/tinh-yeu-gioi-tinh.rss", "source_type": "RSS"},
    {"name": "Dân trí - Khoa học", "url": "https://dantri.com.vn/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Dân trí - Nội vụ", "url": "https://dantri.com.vn/rss/noi-vu.rss", "source_type": "RSS"},
    {"name": "Dân trí - Bạn đọc", "url": "https://dantri.com.vn/rss/ban-doc.rss", "source_type": "RSS"},
    {"name": "Dân trí - Tâm điểm", "url": "https://dantri.com.vn/rss/tam-diem.rss", "source_type": "RSS"},
    {"name": "Dân trí - Dmagazine", "url": "https://dantri.com.vn/rss/dmagazine.rss", "source_type": "RSS"},
    {"name": "Dân trí - Infographic", "url": "https://dantri.com.vn/rss/infographic.rss", "source_type": "RSS"},
    {"name": "Dân trí - Photo News", "url": "https://dantri.com.vn/rss/photo-news.rss", "source_type": "RSS"},
    {"name": "Dân trí - DNews", "url": "https://dantri.com.vn/rss/dnews.rss", "source_type": "RSS"},
    {"name": "Dân trí - Tọa đàm trực tuyến", "url": "https://dantri.com.vn/rss/toa-dam-truc-tuyen.rss", "source_type": "RSS"},
    {"name": "Dân trí - Xổ số", "url": "https://dantri.com.vn/rss/xo-so.rss", "source_type": "RSS"},
    {"name": "Dân trí - Interactive", "url": "https://dantri.com.vn/rss/interactive.rss", "source_type": "RSS"},
    {"name": "Dân trí - Tết", "url": "https://dantri.com.vn/rss/tet.rss", "source_type": "RSS"},
    {"name": "Dân trí - Photo Story", "url": "https://dantri.com.vn/rss/photo-story.rss", "source_type": "RSS"},
    {"name": "Dân trí - D-Buzz", "url": "https://dantri.com.vn/rss/d-buzz.rss", "source_type": "RSS"},
    {"name": "Dân trí - Thời tiết", "url": "https://dantri.com.vn/rss/thoi-tiet.rss", "source_type": "RSS"},
    {"name": "Dân trí - DT360", "url": "https://dantri.com.vn/rss/dt360.rss", "source_type": "RSS"},

    # ── VTV ──
    {"name": "VTV - Chính trị", "url": "https://vtv.vn/rss/chinh-tri.rss", "source_type": "RSS"},
    {"name": "VTV - Công nghệ", "url": "https://vtv.vn/rss/cong-nghe.rss", "source_type": "RSS"},
    {"name": "VTV - Đời sống", "url": "https://vtv.vn/rss/doi-song.rss", "source_type": "RSS"},
    {"name": "VTV - Giáo dục", "url": "https://vtv.vn/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "VTV - Trang chủ", "url": "https://vtv.vn/rss/home.rss", "source_type": "RSS"},
    {"name": "VTV - Kinh tế", "url": "https://vtv.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "VTV - Pháp luật", "url": "https://vtv.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "VTV - Thế giới", "url": "https://vtv.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "VTV - Thể thao", "url": "https://vtv.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "VTV - Văn hóa Giải trí", "url": "https://vtv.vn/rss/van-hoa-giai-tri.rss", "source_type": "RSS"},
    {"name": "VTV - Xã hội", "url": "https://vtv.vn/rss/xa-hoi.rss", "source_type": "RSS"},

    # ── Người Lao động ──
    {"name": "Người Lao động - Trang chủ", "url": "https://nld.com.vn/rss/home.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thời sự", "url": "https://nld.com.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Chính trị", "url": "https://nld.com.vn/rss/thoi-su/chinh-tri.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Xã hội", "url": "https://nld.com.vn/rss/thoi-su/xa-hoi.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Quốc tế", "url": "https://nld.com.vn/rss/quoc-te.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Lao động", "url": "https://nld.com.vn/rss/lao-dong.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Bạn đọc", "url": "https://nld.com.vn/rss/ban-doc.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Kinh tế", "url": "https://nld.com.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Sức khỏe", "url": "https://nld.com.vn/rss/suc-khoe.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Giáo dục", "url": "https://nld.com.vn/rss/giao-duc-khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Pháp luật", "url": "https://nld.com.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Văn hóa văn nghệ", "url": "https://nld.com.vn/rss/van-hoa-van-nghe.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Giải trí", "url": "https://nld.com.vn/rss/giai-tri.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thể thao", "url": "https://nld.com.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Du lịch", "url": "https://nld.com.vn/rss/du-lich.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Thị trường", "url": "https://nld.com.vn/rss/thi-truong.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Đời sống", "url": "https://nld.com.vn/rss/doi-song.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Khoa học", "url": "https://nld.com.vn/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Người Lao động - Góc nhìn", "url": "https://nld.com.vn/rss/goc-nhin.rss", "source_type": "RSS"},

    # ── Báo Nhân Dân ──
    {"name": "Báo Nhân Dân - Chính trị", "url": "https://nhandan.vn/rss/chinh-tri.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Giáo dục", "url": "https://nhandan.vn/rss/giao-duc.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Khoa học", "url": "https://nhandan.vn/rss/khoa-hoc.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Kinh tế 515", "url": "https://nhandan.vn/rss/kinh-te-515.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Kinh tế", "url": "https://nhandan.vn/rss/kinh-te.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Pháp luật", "url": "https://nhandan.vn/rss/phap-luat.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Thế giới", "url": "https://nhandan.vn/rss/the-gioi.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Thể thao", "url": "https://nhandan.vn/rss/the-thao.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Văn hóa", "url": "https://nhandan.vn/rss/van-hoa.rss", "source_type": "RSS"},
    {"name": "Báo Nhân Dân - Xã hội 582", "url": "https://nhandan.vn/rss/xa-hoi-582.rss", "source_type": "RSS"},

    # ── VOV ──
    {"name": "VOV - Thời sự", "url": "https://vov.vn/rss/thoi-su-213.rss", "source_type": "RSS"},
    {"name": "VOV - Chính trị", "url": "https://vov.vn/rss/chinh-tri-214.rss", "source_type": "RSS"},
    {"name": "VOV - Xã hội", "url": "https://vov.vn/rss/xa-hoi-215.rss", "source_type": "RSS"},
    {"name": "VOV - Kinh tế", "url": "https://vov.vn/rss/kinh-te-212.rss", "source_type": "RSS"},
    {"name": "VOV - Thế giới", "url": "https://vov.vn/rss/the-gioi-216.rss", "source_type": "RSS"},
    {"name": "VOV - Pháp luật", "url": "https://vov.vn/rss/phap-luat-217.rss", "source_type": "RSS"},
    {"name": "VOV - Thể thao", "url": "https://vov.vn/rss/the-thao-218.rss", "source_type": "RSS"},
    {"name": "VOV - Văn hóa Giải trí", "url": "https://vov.vn/rss/van-hoa-giai-tri-219.rss", "source_type": "RSS"},
    {"name": "VOV - Đời sống Gia đình", "url": "https://vov.vn/rss/doi-song-gia-dinh-220.rss", "source_type": "RSS"},
    {"name": "VOV - Khoa học Công nghệ", "url": "https://vov.vn/rss/khoa-hoc-cong-nghe-221.rss", "source_type": "RSS"},

    # ── Báo Đầu tư ──
    {"name": "Báo Đầu tư - Bất động sản", "url": "https://baodautu.vn/rss/bat-dong-san.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Đầu tư", "url": "https://baodautu.vn/rss/dau-tu.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Doanh nghiệp", "url": "https://baodautu.vn/rss/doanh-nghiep.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Quốc tế", "url": "https://baodautu.vn/rss/quoc-te.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Tài chính Ngân hàng", "url": "https://baodautu.vn/rss/tai-chinh-ngan-hang.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Thời sự", "url": "https://baodautu.vn/rss/thoi-su.rss", "source_type": "RSS"},
    {"name": "Báo Đầu tư - Trang chủ", "url": "https://baodautu.vn/trang-chu.rss", "source_type": "RSS"},

    # ── Web Sources ──
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
    
    # 1. Seed Keywords (idempotent: only insert if it doesn't exist)
    keywords_col = db.keywords
    print("Checking and seeding default keywords...")
    added_kws = 0
    for kw in DEFAULT_KEYWORDS:
        existing = await keywords_col.find_one({"value": kw})
        if not existing:
            doc = {
                "value": kw,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await keywords_col.insert_one(doc)
            added_kws += 1
    print(f"✅ Seeding keywords: added {added_kws} new keywords.")

    # 2. Seed Sources (idempotent: only insert if url doesn't exist)
    sources_col = db.sources
    print("Checking and seeding default sources...")
    added_sources = 0
    for src in DEFAULT_SOURCES:
        existing = await sources_col.find_one({"url": src["url"]})
        if not existing:
            doc = {
                "name": src["name"],
                "url": src["url"],
                "source_type": src["source_type"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await sources_col.insert_one(doc)
            added_sources += 1
    print(f"✅ Seeding sources: added {added_sources} new sources.")

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
