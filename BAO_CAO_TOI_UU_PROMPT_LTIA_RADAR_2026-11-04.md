# Phân tích Chuyên sâu & Định hướng Tối ưu hóa `prompts.py` cho Hệ thống LTIA Radar (Cập nhật Thực trạng Tháng 11/2026)

> **Trạng thái tài liệu**: Bản phân tích kỹ thuật & thiết kế Prompt v2.0 (`ai_draft` — CHƯA phê duyệt chính thức, phục vụ rà soát và triển khai kỹ thuật).
> **Tệp mã nguồn đi kèm**: `_OUTPUTS_SAN_PHAM/01_bao_cao_chuyen_mon/prompts.py`

---

## 1. Chẩn đoán 6 Điểm mù & Lỗi Kỹ thuật trong `prompts.py` Hiện hữu (và Spec Dự thảo)

Qua đối chiếu mã nguồn `prompts.py` hiện hữu, tài liệu đặc tả `PROMPT_ENGINEERING_SPEC.md`, hồ sơ **Báo cáo số 424/BC-BXD ngày 27/10/2026 của Bộ Xây dựng** (`[CĂN CỨ PHÁP LUẬT CHUNG]`, trang 1–18 & Phụ lục 1–3) và hệ thống Quy chế của ACV (`[CĂN CỨ PHÁP LUẬT CHUNG]`), bộ prompt đang chạy bộc lộ **6 hạn chế cốt lõi** làm giảm chất lượng phân tích của LLM:

### 1.1. Lệch pha nghiêm trọng về Giai đoạn Dự án & Trọng tâm Rủi ro (Temporal Drift)
- **Hiện trạng trong `prompts.py` cũ (dòng 38–50)**: Vẫn neo cứng ở bối cảnh năm 2024 – đầu 2025: ghi `Mốc khánh thành: 02/09/2026`, chỉ liệt kê vỏn vẹn **02 gói thầu** (`5.10` và `4.6`), lấy *"thiếu cát san lấp"* làm ví dụ mẫu số 1 cho cả chế độ đơn lẻ lẫn Batch.
- **Thực tế tại tháng 11/2026** (theo Báo cáo `424/BC-BXD` ngày 27/10/2026, tr. 2–15):
  - Mốc `02/09/2026` đã đi qua; Gói thầu `3.4` (san nền và thoát nước) **đã hoàn thành** cùng `2.4`, `5.6`, `6.12`.
  - Tâm điểm điều hành hiện nay là **phương án đưa Cảng vào khai thác thương mại từ ngày `24/12/2026`** do ACV đề xuất (công bố tin tức hàng không AIRAC ngày `12/11/2026`) và quan điểm của Bộ Xây dựng: **không đánh đổi an toàn, an ninh, chất lượng để chạy theo tiến độ**, cảnh báo rủi ro **vừa khai thác vừa thi công hoàn thiện**.
  - Rủi ro đường găng thực sự hiện nằm ở **04/16 gói thầu của DATP 3 có nguy cơ không hoàn thành 100% trong tháng 12/2026** (`4.8`, `5.10`, `7.8`, `11.5`), áp lực nén thời gian **vận hành thử ORAT** (~3 tháng, 55 kịch bản), **chuỗi thủ tục nghiệm thu – cấp phép liên ngành tháng 11–12/2026**, và **lộ trình 3 bước chuyển đổi đường bay quốc tế từ Tân Sơn Nhất sang Long Thành**.

### 1.2. Thiếu hụt Bức tranh Thể chế 2025–2026 & Vai trò Kép của ACV – Cảng HKQT Long Thành
- **Thay đổi thể chế nhà nước (`[CĂN CỨ PHÁP LUẬT CHUNG]`, BC `424/BC-BXD` tr. 1, 7, 9, 16–18)**:
  - **Bộ Xây dựng** (sau hợp nhất với Bộ GTVT) là cơ quan chủ quản cả lĩnh vực xây dựng lẫn hàng không dân dụng (chỉ đạo trực tiếp **Cục Hàng không Việt Nam**, **Cục Giám định nhà nước về chất lượng CTXD**, **Cục Đăng kiểm Việt Nam**). Prompt cũ vẫn mặc định chỉ biết `"Bộ GTVT"`.
  - **Bộ Tài chính** là cơ quan đại diện chủ sở hữu vốn nhà nước tại ACV (thể hiện trực tiếp trên tiêu đề Quyết định `175/QĐ-HĐQT` ngày 26/03/2026).
  - **Bộ Công an (Cục Quản lý xuất nhập cảnh – Cục A08)** là cơ quan quản lý nhà nước và phê duyệt **An ninh hàng không** (Chương trình ANHK, Kế hoạch khẩn nguy, thẻ/giấy phép kiểm soát an ninh theo Thông tư `31/2025/TT-BCA` và `14/2026/TT-BCA`).
  - **Bộ Nông nghiệp và Môi trường** thẩm định và cấp **Giấy phép môi trường**.
- **Khoảng trống về ACV và Cảng HKQT Long Thành (LTIA)**:
  - Prompt cũ chỉ coi ACV là *"Chủ đầu tư"* xây dựng mà chưa phân biệt **vai trò kép** của ACV:
    1. **Chủ đầu tư DATP 3** qua **Ban Quản lý dự án Cảng HKQT Long Thành (Ban QLDA Long Thành)**.
    2. **Người khai thác cảng (Airport Operator)** qua **Cảng HKQT Long Thành (LTIA)** — Chi nhánh cấp 1 trực thuộc ACV thành lập theo Quyết định `452/QĐ-HĐQT` (08/9/2025), vận hành theo Quy chế `175/QĐ-HĐQT` (26/03/2026) (`[CĂN CỨ PHÁP LUẬT CHUNG]`, trang 3–6) gồm Ban Giám đốc, 08 Phòng/Văn phòng chuyên môn (trong đó có Phòng KTCN-MT, Phòng An toàn - KSCL — đối chiếu `[DỰ ÁN CỤC BỘ]` `01_TAI_LIEU_THAM_KHAO/Phân công nhiệm vụ/20261008 Danh sach he thong trang thiet bi cong trinh.docx`) và **04 Trung tâm khai thác** (*Trung tâm Điều hành sân bay Long Thành / APOC, Trung tâm Khai thác ga, Trung tâm Khai thác khu bay, Trung tâm Dịch vụ kỹ thuật hàng không*), song hành cùng 02 chi nhánh chuyên ngành **LAFS** (nhiên liệu HK — `649/QĐ-HĐQT`) và **LACS** (hàng hóa HK — `651/QĐ-HĐQT`).

> **Đính chính sai sót dữ kiện nghiêm trọng trong tài liệu `PROMPT_ENGINEERING_SPEC.md` (Mục 4.3, dòng 161):**
> Tài liệu Spec dự thảo đang ghi nhầm **Gói thầu 7.8** là *"Thi công phần thân Tháp kiểm soát không lưu thuộc DATP 2 — VATM (Tổng công ty 36)"*.
> Đối chiếu chính xác **Báo cáo số 424/BC-BXD** (`[CĂN CỨ PHÁP LUẬT CHUNG]`, trang 2 & trang 10):
> - **Gói thầu 7.8** thuộc **DATP 3 (Chủ đầu tư ACV)**: *"Thi công xây dựng, lắp đặt thiết bị công trình Nhà ga hàng hóa số 1 và các công trình phụ trợ còn lại"* (Liên danh **HANTA2**: Coteccons – Hancorp – ATAD) — đây là **1 trong 4 gói đường găng đỏ có nguy cơ trễ hạn tháng 12/2026**.
> - Phần thân **Đài kiểm soát không lưu cao 123m** thuộc **DATP 2 (Chủ đầu tư VATM)** là **Gói thầu XD02** (Liên danh Tổng công ty 36 – NEWTATCO – VNCC).

### 1.3. Lỗi "Đứt gãy Bộ lọc Giao diện" trên trường `target_scope`
- Giao diện Next.js (`dashboard/page.tsx`, `articles/page.tsx`) truy vấn cứng MongoDB bằng toán tử `target_scope: {"$in": [value]}` với **7 nhãn cố định**: `"Toàn dự án"`, `"Gói thầu 5.10"`, `"Gói thầu 4.6"`, `"San nền"`, `"Giao thông"`, `"Nhà ga"`, `"Đường cất hạ cánh"`.
- `prompts.py` cũ hướng dẫn LLM sinh `"target_scope": ["Hạ tầng kết nối"]` (dòng 60, 172, 187) → người dùng chọn bộ lọc **`"Giao thông"`** trên UI sẽ bị sót toàn bộ tin cao tốc/đường kết nối. Tương tự, Ví dụ 3, 5, 6, 7 chỉ trả `["Gói thầu 5.10"]` mà thiếu `"Nhà ga"` → chọn bộ lọc **`"Nhà ga"`** sẽ trả về rỗng.

### 1.4. Hai Lỗi Logic Gom cụm (`Clustering`) trong `BATCH_SYSTEM_PROMPT`
1. **Tiêu chí chọn `source_indices[0]` bị ngược ưu tiên**: Prompt cũ xếp *"đăng sớm nhất"* ngang hàng làm tiêu chí đặt lên đầu `source_indices[0]`, dễ lấy bản tin vắn đầu tiên thay vì bài phân tích đầy đủ từ báo chính thống làm `primary_article` trên Dashboard.
2. **Nguy cơ gom chung các bài `is_relevant: false`**: Chưa cấm gom các bài không liên quan khác chủ đề vào cùng một mảng `source_indices`, làm trộn URL trích dẫn rác trong DB.

### 1.5. Nguy cơ "Rò rỉ Ngữ cảnh Nền" (Context-Bleed Hallucination) khi mở rộng `_CONTEXT`
- Nếu không đặt rào chắn tách biệt rõ ràng giữa `_CONTEXT` và dữ liệu bài báo, LLM dễ tự động chép thông tin từ `_CONTEXT` (như tên nhà thầu `"Vietur"`, con số `"35.000 tỷ"`) vào `key_entities` và `executive_summary` dù bài báo gốc không hề nhắc tới.

### 1.6. Ràng buộc Ngân sách Token Kép giữa Gemini (Primary) và Groq (Fallback)
- Hệ thống dùng song song `gemini.py` (kích hoạt **Implicit Context Caching** khi tiền tố prompt tĩnh vượt ngưỡng ~2.048 token) và `groq_llm.py` (luồng dự phòng chịu giới hạn **TPM Free Tier ~12.000 token/phút**). Do đó cần nén mật độ thông tin của prompt trong ngưỡng **~9.000–9.500 token (`o200k_base`)** để vừa tối ưu Gemini Caching vừa không chạm trần `RateLimitError` của Groq.

---

## 2. Tổng hợp 7 Hướng Điều chỉnh Cốt lõi Đạt Chất lượng Đầu ra Tối ưu

1. **Nạp Bản đồ Tri thức Nén Mật độ Cao**: Bao phủ đầy đủ 4 DATP, toàn bộ 16/16 gói thầu DATP 3 chia theo đúng 3 nhóm trạng thái thực tế của Báo cáo `424/BC-BXD` (4 gói đã xong: `2.4, 3.4, 5.6, 6.12`; 8 gói về đích 12/2026: `4.6, 4.12, 4.7, 4.9, 4.11, 2.10, 7.8a, 5.11`; 4 gói đường găng đỏ: `4.8, 5.10, 7.8, 11.5`), gói `XD02` của VATM, điểm nghẽn Express Cargo của DATP 4, và mô hình tổ chức Cảng HKQT Long Thành (`VVLT`/`LTH`, 8 phòng, 4 trung tâm, LAFS, LACS).
2. **Cơ chế Gắn nhãn Kép (`Dual-Tagging`) cho `target_scope`**: Mọi kết quả `is_relevant=true` bắt buộc chứa ít nhất 1 trong 7 nhãn neo của Dropdown Frontend đi kèm mã gói thầu/hạng mục chi tiết.
3. **Hiệu chỉnh Thang `impact_level` và `category` theo Rủi ro Thực chiến Cuối Năm 2026**: Bao quát đầy đủ rủi ro chậm 4 gói găng, nghẽn thanh toán – thẩm định giá – mỏ vật liệu, chuỗi cấp phép tiền khai thác tháng 11–12/2026 (HĐKTNN/Cục Giám định NN, GP môi trường, PCCC, Chương trình ANHK Cục A08, GCN khai thác cảng Cục HKVN), lỗi tích hợp ORAT, rủi ro vừa khai thác vừa thi công, kiến nghị lùi lịch chuyển khai thác của IATA/hãng bay quốc tế/TSA Mỹ, và nguy cơ ùn tắc nút giao An Phú (Q2/2027).
4. **Tường lửa "Context vs. Evidence"**: Dùng `_CONTEXT` để nhận diện liên quan, gán `target_scope` và định cỡ `impact_level`, nhưng cấm tuyệt đối đưa thông tin ngoài văn bản bài báo vào `key_entities` và `executive_summary`.
5. **Chuẩn hóa Gom cụm Batch**: Ưu tiên bài đầy đủ nhất + nguồn báo chính thống uy tín nhất lên `source_indices[0]`; tách riêng từng bài `is_relevant=false` khác chủ đề; bảo toàn 100% tập index `0..N-1`.
6. **Làm mới Bộ Few-Shot Examples**: Cập nhật 8 ví dụ đơn lẻ + 4 cụm ví dụ Batch phản ánh trực diện mặt cắt tin tức cuối năm 2026.
7. **Lộ trình Kiến trúc Mở rộng cho Backend (Tùy chọn)**: Tách lớp `DYNAMIC_PROJECT_STATE` trên MongoDB để cập nhật mốc tiến độ hàng tháng không cần sửa code; bật `CachedContent` tường minh trên Gemini SDK để giảm 75% chi phí input token.

---

## 3. Nguồn Đối chiếu & Trích dẫn

- `[CĂN CỨ PHÁP LUẬT CHUNG]` **Báo cáo số 424/BC-BXD ngày 27/10/2026 của Bộ Xây dựng** (*về các điều kiện và công tác chuẩn bị đưa CHKQT Long Thành giai đoạn 1 vào vận hành, khai thác*, trang 1–18, Phụ lục 1–3).
- `[CĂN CỨ PHÁP LUẬT CHUNG]` **Quyết định số 452/QĐ-HĐQT ngày 08/9/2025**, **Quyết định số 175/QĐ-HĐQT ngày 26/03/2026**, **Quyết định số 649/QĐ-HĐQT** và **651/QĐ-HĐQT ngày 04/12/2025** của HĐQT ACV (`ACV KB/ACV-Quy chế, Quy định`).
- `[DỰ ÁN CỤC BỘ]` `01_TAI_LIEU_THAM_KHAO/Phân công nhiệm vụ/20261008 Danh sach he thong trang thiet bi cong trinh.docx`.
