# TÀI LIỆU KHỞI TẠO DỰ ÁN: HỆ THỐNG RADAR CẢNH BÁO SỚM & QUẢN TRỊ KHỦNG HOẢNG SÂN BAY LONG THÀNH (LTIA EARLY WARNING SYSTEM)

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

Dự án Cảng Hàng không Quốc tế Long Thành (LTIA) có mốc tiến độ khánh thành cực kỳ nghiêm ngặt vào ngày 01/12/2026. Để quản trị rủi ro thông tin, Hệ thống "Radar Cảnh báo sớm" được xây dựng nhằm tự động thu thập, phân tích (bằng AI) và cảnh báo các thông tin từ báo chí, diễn đàn mạng xã hội. Mục tiêu là phát hiện sớm các vấn đề về tiến độ, chất lượng kỹ thuật, an toàn lao động, và dư luận tiêu cực để Ban Quản lý Dự án (PMU) có hành động can thiệp kịp thời.

## 2. LỘ TRÌNH TRIỂN KHAI (IMPLEMENTATION PHASES)

Dự án được chia thành 3 giai đoạn để đảm bảo có sản phẩm dùng được ngay (MVP) và mở rộng an toàn, không rủi ro:

### 2.1. Giai đoạn 1: Xây dựng MVP (Minimum Viable Product) - Tháng 1

- **Mục tiêu:** Hoàn thiện pipeline cơ bản cho báo chí chính thống và thiết lập bộ khung hệ thống.
- **Tính năng:**
  - Setup NextJS Dashboard cơ bản (Quản lý Keywords, Nguồn tin).
  - Crawler lấy tin từ Báo chí (RSS và quét HTML cơ bản).
  - Tích hợp Google Gemini 2.5 Flash API (chưa cần Redis Queue nếu lượng tin thấp).
  - Thiết lập MongoDB Atlas và lưu trữ dữ liệu.
  - Gửi thông báo Telegram cho các tin có `impact_level == CRITICAL`.

### 2.2. Giai đoạn 2: Scale-up & Tích hợp Message Broker - Tháng 2

- **Mục tiêu:** Đảm bảo hệ thống chịu tải tốt, không vi phạm Rate Limit của LLM, và mở rộng nguồn thu thập.
- **Tính năng:**
  - Triển khai Upstash Redis và Celery/ARQ làm Background Worker.
  - Thiết lập Rate Limit (10 tasks/phút) để lấy dần tin tức đưa cho Gemini xử lý.
  - Phát triển Crawler bóc tách dữ liệu từ các diễn đàn lớn (Otofun, Voz).
  - Cải tiến Prompt Engineering để LLM lọc bỏ các bình luận "rác" trên diễn đàn.
  - Hoàn thiện các biểu đồ thống kê (Chart) trên Dashboard.

### 2.3. Giai đoạn 3: Tối ưu hóa & Mở rộng Mạng Xã Hội - Tháng 3

- **Mục tiêu:** Bắt đầu thu thập dữ liệu khó (Facebook, TikTok) bằng dịch vụ bên thứ 3 và tinh chỉnh hệ thống.
- **Tính năng:**
  - Tích hợp Apify API để quét các group Facebook, kênh Tiktok liên quan đến dự án (nếu chi phí cho phép).
  - Hệ thống Rule Engine nâng cao (Cho phép admin tự định nghĩa điều kiện gửi cảnh báo: Ví dụ `category == MOI_TRUONG` + `sentiment == NEGATIVE`).
  - Chức năng xuất báo cáo (Export PDF/Excel) phục vụ các cuộc họp giao ban hàng tuần của Ban QLDA.

## 3. KIẾN TRÚC HỆ THỐNG & TECH STACK (3-TIER ARCHITECTURE)

Hệ thống sử dụng kiến trúc 3 lớp linh hoạt, tối ưu chi phí (tận dụng Free Tier) và dễ dàng mở rộng.

### 3.1. Frontend (Admin & Dashboard)

- **Framework:** NextJS.
- **Hosting/Deployment:** Vercel (Miễn phí, tích hợp CI/CD tự động từ GitHub).
- **Chức năng lõi:** Quản lý CRUD từ khóa/nguồn tin; Cấu hình Rule Cảnh báo; Dashboard thống kê dữ liệu trực quan.

### 3.2. Backend (Core Engine & Message Broker)

- **Framework:** FastAPI (Python).
- **Hosting/Deployment:** Railway.
- **Message Broker:** Upstash (Serverless Redis).
- **Worker Library:** Celery hoặc ARQ (Async Redis Queue).
- **Chức năng lõi:** RESTful API; Crawler Engine chạy ngầm bằng Cronjob (1 giờ/lần); Quản lý Message Queue; Background Worker tương tác với LLM và Telegram.

### 3.3. Database (Data Layer)

- **Hệ quản trị:** MongoDB Atlas (DBaaS NoSQL, lý tưởng để lưu trữ linh hoạt định dạng JSON từ LLM).

## 4. CHIẾN LƯỢC AI & RATE LIMITING

- **LLM Service:** Google Gemini 2.5 Flash (Sử dụng Free Tier).
- **Design Pattern:** Áp dụng mô hình Interface/Implementation (VD: `ILLMService` -> `GeminiImplementation`) để sẵn sàng thay thế bằng nền tảng khác.
- **Rate Limiting:** Do Gemini Free giới hạn 15 requests/phút (RPM), hệ thống Worker được cấu hình hard-limit: Chỉ xử lý tối đa **10 tasks/phút**.

## 5. LUỒNG DỮ LIỆU (DATA FLOW)

[Cronjob trên FastAPI (1h/lần)]
➜ [Crawler quét News/Forums]
➜ [Đẩy Raw Data vào Upstash Redis Queue]
➜ [FastAPI Worker (Max 10 task/min) lấy task]
➜ [Gọi Gemini API trích xuất/phân tích]
➜ [Lưu Processed Data vào MongoDB Atlas]
➜ [Đánh giá Rule Alert: Nếu CRITICAL/NEGATIVE...]
➜ [Bắn API gửi tin nhắn Telegram cho PMU]
➜ [NextJS query từ MongoDB để hiển thị Dashboard thời gian thực].

## 6. CẤU TRÚC DỮ LIỆU (DATA SCHEMA)

### 6.1. Dữ liệu gốc (Raw Data)

- `source_url` (String): Link gốc của bài viết.
- `domain` (String): Nguồn (vnexpress.net, otofun.net...).
- `title` (String): Tiêu đề.
- `author/poster` (String): Tên tác giả hoặc nickname.
- `raw_text` (String): Toàn văn bài viết.
- `image_links` (Array of Strings): Danh sách URL hình ảnh.
- `publish_time` (Datetime): Thời gian đăng bài.
- `crawl_time` (Datetime): Thời gian hệ thống thu thập.

### 6.2. Dữ liệu xử lý bởi LLM (Processed Data)

- `category` (Array): Dạng tin (Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận...).
- `sentiment` (String): `POSITIVE`, `NEGATIVE`, hoặc `NEUTRAL`.
- `target_scope` (String/Array): Gói thầu (VD: 5.10, 4.6), Hạng mục, hoặc Toàn dự án.
- `impact_level` (String): `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` (Trường quan trọng nhất).
- `key_entities` (Object/Array): Các thực thể liên quan (Tên nhà thầu, lãnh đạo, cơ quan).
- `executive_summary` (String): Tóm tắt cực ngắn (1-2 câu) trọng tâm vấn đề.
- `is_rumor` (Boolean): Đánh dấu cờ (True/False) nhận diện tin đồn chưa kiểm chứng.

## 7. BẢO MẬT & TIÊU CHÍ THÀNH CÔNG (SECURITY & SUCCESS METRICS)

### 7.1. Bảo mật & Phân quyền (Security & Auth)

- Vì là hệ thống nội bộ của Ban QLDA, Dashboard cần được bảo vệ bằng cơ chế xác thực (Authentication) cơ bản như **NextAuth** (Đăng nhập bằng tài khoản Google/Email nội bộ).
- Các Endpoints của FastAPI phải được bảo vệ bằng API Key hoặc JWT Token để tránh truy cập trái phép.

### 7.2. Tiêu chí đánh giá hệ thống (Success Metrics/KPIs)

- **Độ trễ cảnh báo (Latency):** Từ khi bài báo/bài post lên mạng đến khi có tin nhắn Telegram phải **< 120 phút** (Gồm 60p chờ Cronjob + thời gian xử lý Queue).
- **Độ chính xác AI (AI Accuracy):** > 90% các tin tức được phân loại đúng `category` và `impact_level` (Sẽ được đánh giá bằng cách Admin report "False Positive" trên Dashboard).
- **Tính khả dụng (Uptime):** Backend và Crawler hoạt động ổn định không crash khi đối mặt với sự thay đổi DOM của các trang web nguồn (cần cơ chế Error Logging qua Telegram cho Developer).
