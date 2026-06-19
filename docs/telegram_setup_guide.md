# Hướng Dẫn Tích Hợp và Cấu Hình Cảnh Báo Telegram

Hệ thống **LTIA Radar** hỗ trợ tự động gửi cảnh báo qua Telegram khi phát hiện các tin tức có mức độ ảnh hưởng lớn (CRITICAL, HIGH...) hoặc theo các quy tắc cấu hình cụ thể. Tài liệu này hướng dẫn chi tiết cách tạo bot Telegram, lấy Chat ID và cấu hình vào hệ thống.

---

## Bước 1: Tạo Telegram Bot qua @BotFather

1. Mở ứng dụng Telegram và tìm kiếm người dùng **`@BotFather`** (có tích xanh xác minh).
2. Nhấp **Start** hoặc gửi tin nhắn `/newbot` để bắt đầu tạo bot mới.
3. **Nhập tên hiển thị cho Bot** (Ví dụ: `LTIA Radar Bot`).
4. **Nhập username cho Bot** (Phải kết thúc bằng chữ `bot`, ví dụ: `ltia_radar_bot`).
5. Sau khi tạo thành công, `@BotFather` sẽ gửi cho bạn một đoạn **Token** (HTTP API Token).
   * *Ví dụ thực tế của dự án: `8982362990:AAH4IadIu40CKHXQqtm80wIzv8TsmQAolH4`*
   * **Lưu trữ Token này cẩn thận** và không chia sẻ công khai. Đây chính là `TELEGRAM_BOT_TOKEN`.

---

## Bước 2: Lấy Chat ID nhận cảnh báo

Hệ thống có thể gửi cảnh báo đến **cá nhân**, **nhóm chat (Group)** hoặc **kênh tin tức (Channel)**.

### Trường hợp 1: Nhận tin nhắn cá nhân (Direct Message)

1. Tìm kiếm và bắt đầu trò chuyện với bot bạn vừa tạo. Nhấp **Start** (`/start`).
2. Mở trình duyệt web hoặc công cụ API và truy cập URL sau (thay thế `<BOT_TOKEN>` bằng Token ở Bước 1):
   ```http
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
3. Tìm kiếm giá trị `"id"` trong phần `"chat"` của kết quả JSON trả về.
   * *Ví dụ: `"chat":{"id":987654321,"first_name":...}`. Chat ID cá nhân thường là một số nguyên dương (ví dụ: `987654321`).*
4. Hoặc cách nhanh nhất: tìm kiếm bot **`@userinfobot`** trên Telegram, nhấn **Start**, bot sẽ trả về Chat ID cá nhân của bạn ngay lập tức.

### Trường hợp 2: Nhận tin nhắn vào Nhóm (Telegram Group)

1. Tạo một nhóm Telegram mới hoặc sử dụng nhóm hiện tại.
2. Thêm bot vừa tạo ở Bước 1 vào nhóm với tư cách thành viên.
3. Gửi một tin nhắn bất kỳ vào nhóm (ví dụ: `/test`).
4. Truy cập URL getUpdates tương tự như trên:
   ```http
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
5. Tìm kiếm đối tượng `"chat"` tương ứng với nhóm của bạn. Chat ID của nhóm luôn bắt đầu bằng dấu trừ `-`.
   * *Ví dụ thực tế từ nhóm LTIA News Radar của bạn: `-1004327895180`.*

### Trường hợp 3: Nhận tin nhắn vào Kênh (Telegram Channel)

1. Tạo một Kênh (Channel) công khai hoặc riêng tư.
2. Thêm bot vừa tạo vào làm Quản trị viên (Administrator) của kênh với quyền gửi tin nhắn (`Post Messages`).
3. Cách lấy Chat ID của Kênh:
   * Nếu kênh là công khai: Chat ID chính là tên username của kênh bắt đầu bằng ký tự `@` (ví dụ: `@ltia_radar_alerts`).
   * Nếu kênh riêng tư: Hãy gửi một bài đăng bất kỳ vào kênh, sau đó chuyển tiếp bài đăng đó đến bot `@username_to_id_bot` để lấy Chat ID của kênh (luôn bắt đầu bằng `-100`).

---

## Bước 3: Cấu Hình Biến Môi Trường

Mở file cấu hình `.env` tại thư mục gốc của dự án và bổ sung/chỉnh sửa thông tin bot của bạn:

```env
# --- Telegram Alerting ---
TELEGRAM_BOT_TOKEN=8982362990:AAH4IadIu40CKHXQqtm80wIzv8TsmQAolH4
TELEGRAM_CHAT_ID=-1004327895180
```

> [!IMPORTANT]
> Sau khi thay đổi file `.env`, bạn cần áp dụng cấu hình mới bằng cách khởi động lại container backend qua docker compose:
> ```bash
> docker compose up -d
> ```

---

## Bước 4: Thiết lập Quy Tắc Cảnh Báo (Alert Rules)

Hệ thống cho phép cấu hình linh hoạt gửi tin nhắn đến các Chat ID khác nhau cho từng quy tắc riêng biệt:

1. Truy cập trang Quản trị tại: [http://localhost:3000/admin](http://localhost:3000/admin).
2. Vào phần **Cài đặt** -> **Cấu hình Cảnh báo / Alert Rules**.
3. Tại đây bạn có thể kích hoạt/vô hiệu hóa các quy tắc hoặc tạo quy tắc mới:
   * **Mặc định**: Nếu để trống hoặc đặt là `default_chat_id` trong Rule, hệ thống sẽ tự động sử dụng Chat ID mặc định được cấu hình trong file `.env` (`TELEGRAM_CHAT_ID`).
   * **Tùy biến**: Bạn có thể chỉ định một Chat ID riêng biệt cho từng Rule để phân chia luồng tin (ví dụ: tin CRITICAL gửi vào Group của Ban giám đốc, tin HIGH gửi vào Group kỹ thuật).

---

## Bước 5: Kiểm Tra Hoạt Động (Testing)

Bạn có thể gửi thử tin nhắn kiểm tra trực tiếp từ trang Admin:

1. Tại trang **Cài đặt** -> **Cấu hình Cảnh báo**, tìm nút **Kiểm tra kết nối Telegram (Test Bot)**.
2. Nhập Chat ID cần kiểm tra hoặc bấm nút test cho rule và gửi test.
3. Nếu thành công, bạn sẽ nhận được tin nhắn thử nghiệm từ Bot trong Telegram với nội dung:
   > 🧪 **LTIA RADAR — TEST ALERT**
   >
   > ✅ Cấu hình Telegram hoạt động bình thường!

---

## Định Dạng Cảnh Báo Tin Tức

Khi một tin tức khớp với quy tắc cảnh báo, Bot sẽ gửi tin nhắn HTML có cấu trúc rõ ràng:
* **Mức độ rủi ro**: Được đánh dấu bằng các emoji trực quan (🔴 🚨 CRITICAL, 🟠 ⚠️ HIGH, etc.).
* **Tiêu đề tin tức**: In đậm rõ ràng.
* **Tóm tắt nội dung**: Được định dạng in nghiêng, súc tích do Gemini AI tổng hợp.
* **Nhãn phân loại & Đối tượng liên quan**: Danh sách danh mục, phạm vi gói thầu, và các đơn vị/đối tượng bị ảnh hưởng.
* **Nguồn tin liên quan**: Liệt kê đầy đủ các nguồn báo chí (VnExpress, Tuổi Trẻ...) kèm link trực tiếp đến bài viết gốc dưới dạng siêu liên kết gọn gàng.
