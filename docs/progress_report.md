# BÁO CÁO TIẾN ĐỘ & CẤU TRÚC HỆ THỐNG RADAR CẢNH BÁO SỚM LTIA

Báo cáo chi tiết về cấu trúc mã nguồn hiện tại, các chức năng đã hoàn thành trong Phase 1 (MVP) và kế hoạch thực hiện các giai đoạn tiếp theo.

---

## I. Cấu Trúc Chi Tiết Ứng Dụng (App Structure)

Dự án được xây dựng theo mô hình **3-Tier Architecture** kết hợp với **Clean Architecture** (ở Backend) và **Next.js App Router** (ở Frontend), được container hóa toàn bộ bằng Docker Compose.

```
ltia-radar/
├── .agent/                    # Memory Bank quản lý context của AI Agent
├── backend/                   # Backend API (FastAPI)
│   ├── app/
│   │   ├── api/               # Lớp API (Routing và Dependencies Injection)
│   │   │   ├── routes/        # Định nghĩa các endpoint (CRUD Sources, Keywords, Articles, Rules...)
│   │   │   └── dependencies.py# Quản lý khởi tạo & inject các service (DI Pattern)
│   │   ├── application/       # Lớp nghiệp vụ (Use Cases)
│   │   │   └── crawl_news.py  # Điều phối pipeline Crawl → Dedup → AI Process → Store → Alert
│   │   ├── domain/            # Lớp Domain chứa thực thể cốt lõi và interface
│   │   │   ├── entities/      # Định nghĩa các Pydantic model (Source, Keyword, RawData, ProcessedData, AlertRule)
│   │   │   └── interfaces/    # Định nghĩa các Abstract Base Classes (ICrawlerBase, ILLMService, IAlertService)
│   │   ├── infrastructure/    # Lớp Hạ tầng (Triển khai các interface từ Domain)
│   │   │   ├── alerting/      # Telegram service gửi tin nhắn cảnh báo định dạng HTML
│   │   │   ├── crawler/       # RSS Crawler (feedparser) và HTML Crawler (BeautifulSoup)
│   │   │   ├── database/      # Kết nối MongoDB (Motor async) và Repository Pattern
│   │   │   └── llm/           # Google Gemini 2.5 Flash Client (trích xuất insight thành JSON)
│   │   ├── scheduler/         # Trình lập lịch tác vụ chạy ngầm định kỳ
│   │   │   └── jobs.py        # Thiết lập APScheduler chạy crawl tự động mỗi 1 giờ
│   │   ├── config.py          # Quản lý cấu hình ứng dụng từ file .env qua Pydantic-Settings
│   │   └── main.py            # File chạy chính của FastAPI (Lifespan hook, CORS)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Frontend Web App (Next.js 15, React, Tailwind CSS)
│   ├── src/
│   │   ├── app/               # Next.js App Router (Dashboard, Sources, Keywords, Articles, Settings...)
│   │   │   ├── articles/      # Trang quản lý và chi tiết các bài báo đã phân tích
│   │   │   ├── dashboard/     # Trang Dashboard tổng quan (Biểu đồ Sentiment, Category, Top rủi ro)
│   │   │   ├── keywords/      # Trang quản trị từ khóa mục tiêu
│   │   │   ├── sources/       # Trang quản trị nguồn tin (Báo chí, RSS)
│   │   │   ├── settings/      # Trang quản trị quy tắc cảnh báo (Alert Rules)
│   │   │   └── globals.css    # Thiết lập giao diện màu tối premium (glassmorphism, gradient)
│   │   ├── components/        # Các component tái sử dụng (Sidebar layout, Chart widgets...)
│   │   └── lib/               # Thư viện client-side (API fetches, utils)
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml         # File Docker Compose khởi động 3 container (mongodb, backend, frontend)
```

### Chi tiết các tệp tin quan trọng:
1. **[backend/app/main.py](file:///home/antigravity/workspace/ltia-radar/backend/app/main.py)**: Khởi tạo ứng dụng FastAPI, kết nối MongoDB thông qua Lifespan event và kích hoạt trình lập lịch scheduler.
2. **[backend/app/application/crawl_news.py](file:///home/antigravity/workspace/ltia-radar/backend/app/application/crawl_news.py)**: Chứa Use Case cốt lõi `CrawlNewsUseCase` điều phối toàn bộ luồng xử lý thông tin thô thành tri thức cảnh báo.
3. **[backend/app/infrastructure/llm/gemini.py](file:///home/antigravity/workspace/ltia-radar/backend/app/infrastructure/llm/gemini.py)**: Triển khai việc gửi tin bài sang Google Gemini, sử dụng kỹ thuật cấu trúc hóa JSON output để phân tích sentiment, impact level, is_rumor và các thực thể liên đới.
4. **[backend/app/infrastructure/alerting/telegram.py](file:///home/antigravity/workspace/ltia-radar/backend/app/infrastructure/alerting/telegram.py)**: Gửi cảnh báo định dạng HTML phong phú (biểu tượng cảnh báo đỏ, tóm tắt ý chính, nút liên kết trực tiếp bài viết) tới nhóm quản lý.
5. **[frontend/src/app/dashboard/page.tsx](file:///home/antigravity/workspace/ltia-radar/frontend/src/app/dashboard/page.tsx)**: Giao diện dashboard hiện đại với các widget Recharts thống kê tỷ lệ tiêu cực/tích cực, xu hướng tin bài và Top 10 rủi ro cần xử lý.

---

## II. Các Bước Đã Thực Hiện (Phase 1 - MVP)

Hệ thống đã triển khai hoàn thiện Phase 1 theo đúng các tiêu chí trong PRD:

### 1. Xây dựng Kiến trúc & Cơ sở dữ liệu (Backend Foundation)
* **MongoDB**: Thiết lập kết nối bất đồng bộ (`motor`). Tạo các chỉ mục tối ưu hiệu năng:
  * Unique index trên `source_url` và `url_hash` để chống trùng lặp dữ liệu thô (US-2.2).
  * Compound index `(target_scope, impact_level, processed_time)` để tối ưu hóa tốc độ truy vấn trên Dashboard (PRD Section 8.2).
* **Repository Pattern**: Tách biệt hoàn toàn tầng logic nghiệp vụ với dữ liệu qua các lớp Repository (`SourceRepository`, `KeywordRepository`, `RawDataRepository`, `ProcessedDataRepository`, `AlertRuleRepository`).
* **Dependency Injection**: Sử dụng dependencies FastAPI để chuyển đổi động các dịch vụ Crawler, LLM và Alert Service, tạo sự linh hoạt tối đa khi mở rộng.

### 2. Crawler Engine (Bộ thu thập tin bài)
* **RSS Crawler**: Sử dụng thư viện `feedparser` để phân tích các kênh RSS báo chí chính thống (VnExpress, Tuổi Trẻ, Thanh Niên...).
* **HTML Crawler**: Kết hợp `httpx` tải trang bất đồng bộ và `BeautifulSoup` để trích xuất sạch nội dung bài viết từ các thẻ HTML, loại bỏ quảng cáo, scripts và các menu điều hướng thừa.
* **Keywords Matching**: Lọc tin bài chứa các từ khóa nhạy cảm liên quan đến Sân bay Long Thành trước khi đẩy vào pipeline xử lý.

### 3. Phân Tích AI (Gemini LLM) & Cảnh Báo Sớm
* **Gemini 2.5 Flash Integration**: Tích hợp mô hình ngôn ngữ thế hệ mới bằng `google-genai`. Cài đặt System Prompt chuyên biệt về dự án LTIA để bóc tách:
  * `sentiment`: Tích cực (POSITIVE), Trung lập (NEUTRAL), Tiêu cực (NEGATIVE).
  * `impact_level`: Nghiêm trọng (CRITICAL), Cao (HIGH), Trung bình (MEDIUM), Thấp (LOW).
  * `category`: Tiến độ, Chất lượng, An toàn, Môi trường, Bồi thường/GPMB, Khác.
  * `is_rumor`: Nhận diện các tin đồn, thông tin chưa được xác thực.
  * `key_entities`: Nhà thầu (Vietur, ACV...), địa danh, gói thầu.
  * `executive_summary`: Bản tóm tắt ngắn gọn 2-3 câu cho lãnh đạo đọc nhanh.
* **Rate Limiting**: Triển khai cơ chế Sliding Window thông qua `asyncio.Semaphore` đảm bảo không vượt quá giới hạn 10 cuộc gọi LLM/phút (tránh bị block API Key Free Tier).
* **Telegram Alerts**: Tự động so khớp tin bài sau khi AI xử lý với các quy tắc cảnh báo (`alert_rules`). Nếu khớp (ví dụ: bài viết Tiêu cực và mức độ CRITICAL), hệ thống tự động soạn tin nhắn và gửi qua Telegram Bot.

### 4. Giao diện Người dùng (Frontend Next.js)
* **Thiết kế Premium**: Giao diện tối màu (Dark Mode) sang trọng, sử dụng Glassmorphism và các đường viền mờ (Backdrop Blur), hỗ trợ hiển thị hoàn hảo trên cả thiết bị di động (Responsive Layout).
* **Dashboard trực quan**: Biểu đồ tròn phân bố Sentiment, biểu đồ cột danh mục và biểu đồ đường xu hướng thời gian thực.
* **Các màn hình chức năng**:
  * *Nguồn tin (Sources)*: Cho phép Thêm/Sửa/Xóa và bật/tắt trạng thái hoạt động của các trang web/RSS.
  * *Từ khóa (Keywords)*: Quản lý bộ lọc từ khóa.
  * *Quy tắc cảnh báo (Alert Rules)*: Thiết lập các điều kiện gửi Telegram (ví dụ: Gửi khi `impact_level` là CRITICAL hoặc HIGH).
  * *Bài viết (Articles)*: Danh sách chi tiết các bài báo đã được AI phân tích cùng chức năng bộ lọc chuyên sâu.

### 5. Hạ tầng Docker & Quản lý mã nguồn
* **Docker Compose**: Đóng gói hoàn chỉnh thành 3 dịch vụ liên kết chẽ. Sử dụng cơ chế mount volume giúp phát triển tiện lợi (Live Reload cho cả backend và frontend).
* **Git & GitHub**: Khởi tạo kho chứa cục bộ, liên kết với kho chứa từ xa `git@github.com:vuhuyduong/ltia-radar.git` và đồng bộ mã nguồn sạch.

---

## III. Các Bước Sẽ Thực Hiện (Phase 2 & Phase 3)

Để hoàn thiện sản phẩm đạt chuẩn Enterprise phục vụ dự án thực tế, các giai đoạn tiếp theo cần tập trung nâng cấp hạ tầng phân tán và khả năng thu thập:

### 1. Phase 2: Nâng cấp Kiến trúc Phân tán & Mạng xã hội (Dự kiến Tháng 2)
- [ ] **Tích hợp Broker-based Queue (Redis + Celery/ARQ)**: 
  * Thay thế cơ chế chạy đồng bộ in-process hiện tại bằng hàng đợi tác vụ bất đồng bộ.
  * Tách biệt API Server và Background Workers giúp hệ thống không bị chậm khi có hàng trăm bài báo được crawl cùng lúc.
- [ ] **Nâng cấp Rate Limiter**: Chuyển đổi sang thuật toán Token Bucket lưu trên Upstash Redis để chia sẻ hạn mức (rate limit) chính xác giữa nhiều worker đang chạy song song.
- [ ] **Mở rộng Crawl Diễn đàn**: Xây dựng bộ cào dữ liệu chuyên sâu cho các diễn đàn lớn của Việt Nam (Otofun, Tinhte, Voz...) để theo dõi sát thảo luận từ người dùng.
- [ ] **Khởi tạo dữ liệu mẫu (Seed Data)**: Tự động nạp sẵn danh sách 15 nguồn báo chí lớn và 20 từ khóa trọng điểm của Sân bay Long Thành khi hệ thống khởi chạy lần đầu tiên.

### 2. Phase 3: Mạng xã hội nâng cao & Rule Engine (Dự kiến Tháng 3)
- [ ] **Giám sát Mạng xã hội (Facebook/TikTok)**: Tích hợp API Listening của bên thứ 3 hoặc xây dựng crawler sử dụng Proxy để rà quét các Fanpage địa phương, Group cư dân xung quanh đại công trường.
- [ ] **Nâng cấp Quy tắc Cảnh báo nâng cao (Complex Rule Engine)**: Hỗ trợ xây dựng các logic rule phức tạp (kết hợp các phép logic AND, OR, NOT) trên giao diện thay vì so khớp đơn giản hiện tại.
- [ ] **Hệ thống Báo cáo Tự động**: Bổ sung tính năng tự động kết xuất báo cáo tổng hợp (PDF, Excel) định kỳ hàng tuần/hàng tháng, gửi trực tiếp qua Telegram hoặc Email cho Lãnh đạo ACV/PMU.
- [ ] **Multi-tenant & Bảo mật**: Hỗ trợ phân quyền người dùng (Giám đốc chỉ xem cảnh báo và dashboard; Chuyên viên có quyền sửa cấu hình).
