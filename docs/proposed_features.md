# BÁO CÁO NGHIÊN CỨU: ĐỀ XUẤT CÁC CHỨC NĂNG BỔ SUNG ĐỂ HOÀN THIỆN HỆ THỐNG LTIA RADAR

Tài liệu này đề xuất các tính năng nâng cao nhằm tối ưu hóa khả năng giám sát, tăng tốc độ xử lý khủng hoảng và hỗ trợ đắc lực cho Ban Quản lý Dự án (PMU) Sân bay Long Thành trước mốc khánh thành ngày 01/12/2026.

---

## 1. Đo lường tốc độ lan truyền khủng hoảng (Crisis Velocity Tracker)
* **Ý tưởng**: Theo dõi tần suất nhắc lại của một chủ đề tiêu cực trên nhiều kênh khác nhau. Hệ thống sẽ tự động tăng mức độ cảnh báo (từ `HIGH` lên `CRITICAL`) nếu:
  * Một bài viết tiêu cực được chia sẻ lại trên quá 3 trang tin trong vòng 2 giờ.
  * Tần suất các tin bài tiêu cực về cùng một từ khóa (ví dụ: "bụi đỏ", "chậm tiến độ gói 5.10") tăng đột biến vượt quá 200% so với trung bình ngày thường.
* **Cách triển khai**:
  * Sử dụng thuật toán so khớp văn bản tương tự (Cosine Similarity hoặc TF-IDF) kết hợp với LLM để gom nhóm bài viết (Clustering).
  * Lưu trữ lịch sử thời gian crawl để tính toán đạo hàm tăng trưởng lượng tin theo thời gian (tin/giờ).
* **Giá trị thực tế**: Giúp PMU phát hiện sớm các chiến dịch truyền thông bẩn hoặc các sự cố đang bắt đầu bùng nổ để kích hoạt kịch bản ứng phó trước khi quá muộn.

## 2. Đề xuất hành động thông minh từ AI (AI Actionable Recommendations)
* **Ý tưởng**: LLM không chỉ tóm tắt và phân tích sắc thái bài viết, mà còn tự động đưa ra các bước hành động cụ thể để xử lý khủng hoảng. Các đề xuất này sẽ được đính kèm trực tiếp vào cảnh báo gửi tới Telegram và hiển thị trên Dashboard.
* **Ví dụ**: Khi phát hiện bài viết tiêu cực về ô nhiễm môi trường tại gói thầu 4.6, AI sẽ đề xuất:
  > **👉 Đề xuất xử lý nhanh:**
  > 1. Chỉ đạo Ban điều hành gói thầu 4.6 điều động ngay 10 xe bồn phun nước dập bụi tại phân khu phía Nam.
  > 2. Phối hợp với UBND Huyện Long Thành để phát đi thông tin về các biện pháp khắc phục ô nhiễm trong 12 giờ tới.
* **Cách triển khai**: Nâng cấp System Prompt của Gemini trong [gemini.py](file:///home/antigravity/workspace/ltia-radar/backend/app/infrastructure/llm/gemini.py), cung cấp thêm ngữ cảnh về danh sách các đầu mối liên hệ của PMU và các kịch bản ứng phó tiêu chuẩn (SOP).
* **Giá trị thực tế**: Rút ngắn thời gian ra quyết định của Lãnh đạo PMU từ hàng giờ xuống còn vài phút, định hướng hành động cực kỳ chuẩn xác ngay tại hiện trường.

## 3. Trình soạn thảo phản hồi báo chí tự động (AI PR Response Generator)
* **Ý tưởng**: Tích hợp nút **"Tạo phản hồi nhanh"** trên giao diện Dashboard bên cạnh mỗi bài viết tiêu cực. Khi bấm nút, Gemini sẽ tự động soạn thảo một bức thư phản hồi hoặc thông cáo báo chí ngắn dựa trên nội dung bài viết và quy chuẩn truyền thông của ACV/PMU.
* **Cách triển khai**:
  * Phát triển thêm Endpoint API `/api/articles/{id}/generate-response`.
  * Cung cấp cho LLM thông tin đính kèm về sự thật hiện trường (qua các báo cáo nội bộ) để LLM biên soạn văn bản phản hồi khách quan, chuẩn mực pháp lý.
* **Giá trị thực tế**: Giúp chuyên viên truyền thông giảm tải áp lực soạn thảo văn bản trong lúc nước sôi lửa bỏng, đảm bảo câu từ chính xác và giữ vững uy tín của dự án.

## 4. Bản đồ hóa rủi ro theo Gói thầu và Địa lý (Spatial Risk Mapping)
* **Ý tưởng**: Phân tích văn bản để xác định vị trí địa lý của sự cố (xã Bình Sơn, Long An, khu tái định cư Lộc An...) hoặc gói thầu liên quan (Gói 5.10 nhà ga, Gói 4.6 đường cất hạ cánh...) và trực quan hóa chúng lên bản đồ nhiệt (Heatmap) trên Dashboard.
* **Cách triển khai**:
  * LLM trích xuất các thực thể địa danh và gói thầu lưu vào cơ sở dữ liệu MongoDB.
  * Frontend sử dụng Mapbox hoặc Leaflet để hiển thị bản đồ dự án với các điểm nóng (Hotspots) rủi ro màu cam/đỏ.
* **Giá trị thực tế**: Cung cấp cái nhìn toàn cảnh trực quan nhất về các khu vực đang có nhiều xung đột lợi ích (ví dụ: bồi thường GPMB) hoặc ô nhiễm để điều chỉnh lực lượng kiểm tra thực địa.

## 5. Quy trình xác thực tin đồn hai chiều (Rumor Verification Workflow)
* **Ý tưởng**: Thiết lập một luồng kiểm chứng tin đồn khép kín. Khi AI gắn cờ `is_rumor = True` cho một tin đăng trên mạng xã hội:
  1. Hệ thống tự động gửi form yêu cầu xác minh qua Telegram đến kỹ sư giám sát hiện trường của gói thầu đó.
  2. Kỹ sư phản hồi nhanh bằng cách bấm nút "Tin đúng" / "Tin sai" kèm ảnh chụp thực tế tại công trường.
  3. Trạng thái tin đồn lập tức được cập nhật trên Dashboard và thông báo ngược lại cho bộ phận truyền thông.
* **Cách triển khai**: Tích hợp cơ chế Telegram Interactive Buttons để giao tiếp hai chiều với nhân sự hiện trường mà không cần họ phải đăng nhập vào dashboard.
* **Giá trị thực tế**: Xử lý triệt để "điểm mù tin đồn", giúp văn phòng truyền thông nắm bắt chính xác thực tế công trường rộng 5000 ha chỉ sau 5-10 phút.

## 6. Chỉ số sức khỏe thương hiệu (Brand Health Index)
* **Ý tưởng**: Tổng hợp sắc thái thảo luận để đưa ra điểm số sức khỏe thương hiệu (Reputation Score) của ACV/PMU theo tuần hoặc tháng.
* **Công thức gợi ý**:
  $$BHI = \frac{Tích cực - Tiêu cực}{Tổng số tin bài} \times 100$$
* **Cách triển khai**: Tạo pipeline aggregation hàng tuần trên MongoDB để tính toán điểm số và vẽ biểu đồ xu hướng.
* **Giá trị thực tế**: Là thước đo định lượng báo cáo trực quan cho Hội đồng quản trị và các cơ quan quản lý cấp trên về tính hiệu quả của các biện pháp truyền thông và thi công.
