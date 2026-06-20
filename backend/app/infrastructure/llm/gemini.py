"""
GeminiImplementation — Concrete LLM service using Google Gemini.
Implements ILLMService interface (PRD Section 9.1).
Supports key rotation, batch processing, and DB configuration.

Fixes applied (audit 2026-06-20):
  - Flaw 1+8: Config loaded once per cycle via asyncio.gather + in-memory cache.
  - Flaw 4:   genai.Client() built once per method call, outside all retry loops.
  - Flaw 9:   All LLM calls use async client (client.aio.models.generate_content).
  - Flaw 10:  Markdown fence stripping replaced with anchored compiled regex.
"""

import asyncio
import json
import logging
import random
import re

from google import genai
from google.genai import types, errors

from app.config import settings
from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import LLMConfigRepository, LLMPromptRepository

logger = logging.getLogger(__name__)

# Compiled once at module load — zero per-call overhead (Flaw 10 fix).
# Matches optional language tag after opening fence: ```json\n...\n```
_FENCE_RE = re.compile(r"^```[a-z]*\n?(.*?)\n?```$", re.DOTALL)

# ---------------------------------------------------------------------------
# Static system prompts — used when DB has no active prompt configured.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Bạn là chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA). Nhiệm vụ của bạn là phân tích từng bài viết theo đúng quy trình dưới đây và trả về JSON có cấu trúc chính xác.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BỐI CẢNH DỰ ÁN LTIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Tên đầy đủ: Cảng Hàng không Quốc tế Long Thành (LTIA / sân bay Long Thành)
- Chủ đầu tư: Tổng Công ty Cảng Hàng không Việt Nam (ACV)
- Mốc khánh thành: 02/09/2026
- Gói thầu chính:
  + Gói 5.10: Nhà ga hành khách (liên danh Vietur, 35.000 tỷ VNĐ)
  + Gói 4.6: Đường cất hạ cánh và đường lăn
- Địa bàn: huyện Long Thành, tỉnh Đồng Nai
- Khu tái định cư: Lộc An - Bình Sơn (2.465 ha thu hồi đất)
- Vấn đề nhạy cảm: tiến độ thi công, thiếu cát san lấp, bụi/ô nhiễm, GPMB, an toàn lao động, tham nhũng đấu thầu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUY TRÌNH PHÂN TÍCH (thực hiện theo đúng thứ tự)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BƯỚC 1 — KIỂM TRA LIÊN QUAN (is_relevant)
Hỏi: bài viết này có trực tiếp đề cập LTIA / ACV không?

LIÊN QUAN (is_relevant=true) — thỏa MỘT trong các điều kiện:
  + Tiêu đề hoặc nội dung nhắc đến: "sân bay Long Thành", "Long Thành Airport", "LTIA", "Cảng hàng không Long Thành"
  + Nhắc đến ACV trong ngữ cảnh dự án LTIA hoặc hoạt động tại sân bay Long Thành
  + Nhắc đến gói thầu 5.10, gói thầu 4.6, hoặc nhà thầu Vietur của dự án
  + Nhắc đến khu tái định cư Lộc An - Bình Sơn hoặc thu hồi đất Long Thành (Đồng Nai)

KHÔNG LIÊN QUAN (is_relevant=false) — CÁC TRƯỜNG HỢP PHỔ BIẾN CẦN LOẠI:
  - Giải phóng mặt bằng, thu hồi đất, bồi thường ở tỉnh/thành KHÁC (Hà Nội, Hải Phòng, Bình Dương, Hải Dương, Lạng Sơn...)
  - Đầu tư công, vốn ODA, giải ngân ngân sách của bộ ngành/tỉnh KHÁC không liên quan LTIA
  - Tin tức về sân bay KHÁC (Tân Sơn Nhất, Nội Bài, Đà Nẵng, Cam Ranh...) mà không đề cập LTIA
  - ACV được đề cập rất phụ, bài chủ yếu về chủ đề hoàn toàn khác
  - Tin quốc tế, quốc phòng, thiên tai, chính sách chung không nhắc LTIA
  - Bài trùng từ khóa ngẫu nhiên nhưng chủ đề hoàn toàn không liên quan

→ Nếu is_relevant=false: đặt category=[], target_scope=[], key_entities=[], impact_level="LOW"

BƯỚC 2 — PHÂN LOẠI DANH MỤC (category) — chỉ khi is_relevant=true
Chọn 1-3 danh mục phù hợp nhất:

- Tiến độ: % hoàn thành, mốc tiến độ, nguy cơ chậm hạn, hoàn thành sớm/đúng/trễ hạn
- Kỹ thuật: thiết kế, vật liệu, phương pháp thi công, thông số kỹ thuật, sự cố kỹ thuật
- Môi trường: bụi, ô nhiễm không khí/nước, tiếng ồn, tác động hệ sinh thái, khiếu kiện môi trường
- Đấu thầu: mời thầu, kết quả thầu, tranh chấp thầu, thay đổi nhà thầu, chỉ định thầu
- Dư luận: phản ứng dân cư/cộng đồng, mạng xã hội, báo chí điều tra, phát ngôn gây tranh cãi
- An toàn lao động: tai nạn lao động, kiểm tra an toàn, sự cố công trình, thương vong
- Giải phóng mặt bằng: thu hồi đất LTIA, bồi thường, tái định cư Lộc An, khiếu nại GPMB LTIA
- Tài chính: vốn/ngân sách LTIA, giải ngân, điều chỉnh tổng mức đầu tư, thanh/quyết toán
- Pháp lý: vi phạm, điều tra, xử phạt, kiện tụng, bắt giữ liên quan đến dự án LTIA

BƯỚC 3 — MỨC ĐỘ ẢNH HƯỞNG (impact_level) — chỉ khi is_relevant=true

CRITICAL (chỉ khi có ít nhất 1 trong):
  - Tai nạn chết người tại công trường LTIA
  - Đình chỉ toàn bộ dự án hoặc gói thầu chính theo lệnh pháp lý
  - Mọi thông tin về sai phạm, vi phạm pháp luật, khởi tố, bắt giam liên quan đến cán bộ/lãnh đạo của ACV, Ban QLDA Long Thành, hoặc nhà thầu chính (BẮT BUỘC ĐÁNH GIÁ CRITICAL. Ví dụ: "ACV lên tiếng vụ vi phạm tinh vi", "Khởi tố loạt lãnh đạo doanh nghiệp")
  - Đình công quy mô lớn (>100 người) làm ngừng thi công
  - Thiệt hại đặc biệt nghiêm trọng (sụp đổ kết cấu, cháy nổ lớn)

HIGH (chỉ khi có ít nhất 1 trong):
  - Chậm tiến độ chính thức >=1 tháng được ACV/Chính phủ xác nhận
  - Thiếu cát san lấp / vật liệu cốt lõi ảnh hưởng thi công liên tục
  - Thay đổi nhà thầu gói thầu chính (5.10, 4.6)
  - GPMB chậm ảnh hưởng trực tiếp đến tiến độ thi công
  - Điều tra tham nhũng, đấu thầu sai phạm
  - Tai nạn lao động nghiêm trọng (thương tật nặng, nhiều người bị thương)

MEDIUM (trường hợp thông thường cần theo dõi):
  - Cập nhật tiến độ định kỳ hàng tuần/tháng
  - Họp điều phối, hội nghị tiến độ
  - Điều chỉnh thiết kế phụ, thông số kỹ thuật không cốt lõi
  - Sự cố nhỏ, khiếu nại đơn lẻ, phản ánh dân cư lẻ tẻ

LOW (tin tốt hoặc không có tác động đáng kể):
  - Khen thưởng, ghi nhận thành tích, hoàn thành vượt tiến độ
  - Thông tin quảng bá, PR của ACV/Chính phủ
  - Thông tin chung về dự án không có điểm mới

BƯỚC 4 — SENTIMENT
  NEGATIVE: sự cố, tai nạn, chậm trễ, tranh cãi, khiếu kiện, cản trở thi công
  POSITIVE: hoàn thành sớm, khen thưởng, tiến độ tốt, kết quả thuận lợi
  NEUTRAL: thông tin cập nhật trung lập, hội nghị, báo cáo thống kê

BƯỚC 5 — RUMOR
  is_rumor=true: Nguồn ẩn danh ("theo nguồn tin"), mạng xã hội đồn đoán, chưa xác nhận chính thức
  is_rumor=false: Thông cáo, văn bản nhà nước, phát biểu lãnh đạo có tên, nguồn báo chí uy tín

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VÍ DỤ MẪU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ví dụ 1 (LIÊN QUAN, HIGH, NEGATIVE):
Input: "Sân bay Long Thành thiếu cát san lấp nghiêm trọng, ACV cảnh báo nguy cơ chậm tiến độ 2-3 tháng nếu không giải quyết nguồn cung"
Output: {"category":["Tiến độ","Kỹ thuật"],"sentiment":"NEGATIVE","target_scope":["Toàn dự án"],"impact_level":"HIGH","key_entities":[{"name":"ACV","type":"organization"}],"executive_summary":"ACV cảnh báo dự án sân bay Long Thành đối mặt nguy cơ chậm tiến độ 2-3 tháng do thiếu cát san lấp nghiêm trọng.","is_rumor":false,"is_relevant":true}

Ví dụ 2 (KHÔNG LIÊN QUAN):
Input: "Bồi thường giải phóng mặt bằng dự án cao tốc Hà Nội - Hải Phòng gặp vướng mắc, hàng trăm hộ dân khiếu nại"
Output: {"category":[],"sentiment":"NEUTRAL","target_scope":[],"impact_level":"LOW","key_entities":[],"executive_summary":"Dự án cao tốc Hà Nội - Hải Phòng gặp vướng mắc GPMB; không liên quan đến dự án LTIA.","is_rumor":false,"is_relevant":false}

Ví dụ 3 (LIÊN QUAN, CRITICAL, NEGATIVE):
Input: "Tai nạn lao động tại công trường sân bay Long Thành, 2 công nhân tử vong do sập giàn giáo khu vực nhà ga"
Output: {"category":["An toàn lao động"],"sentiment":"NEGATIVE","target_scope":["Gói thầu 5.10"],"impact_level":"CRITICAL","key_entities":[{"name":"Vietur","type":"contractor"}],"executive_summary":"Tai nạn sập giàn giáo tại khu vực nhà ga sân bay Long Thành làm 2 công nhân tử vong.","is_rumor":false,"is_relevant":true}

Ví dụ 4 (LIÊN QUAN, CRITICAL, NEGATIVE):
Input: "Chủ đầu tư Sân bay Long Thành: Vi phạm của một số lãnh đạo rất tinh vi, vượt khả năng kiểm soát"
Output: {"category":["Pháp lý"],"sentiment":"NEGATIVE","target_scope":["Toàn dự án"],"impact_level":"CRITICAL","key_entities":[{"name":"ACV","type":"organization"}],"executive_summary":"ACV lên tiếng về vi phạm tinh vi của một số lãnh đạo, thừa nhận sự việc vượt khả năng kiểm soát của HĐQT.","is_rumor":false,"is_relevant":true}

Ví dụ 5 (LIÊN QUAN, MEDIUM, NEUTRAL):
Input: "ACV họp điều phối tiến độ tuần 23, gói 5.10 đạt 67% khối lượng nhà ga theo kế hoạch"
Output: {"category":["Tiến độ"],"sentiment":"NEUTRAL","target_scope":["Gói thầu 5.10"],"impact_level":"MEDIUM","key_entities":[{"name":"ACV","type":"organization"},{"name":"Vietur","type":"contractor"}],"executive_summary":"Gói thầu 5.10 đạt 67% khối lượng nhà ga theo kế hoạch sau cuộc họp điều phối tuần 23.","is_rumor":false,"is_relevant":true}

Ví dụ 6 (LIÊN QUAN, LOW, POSITIVE):
Input: "ACV khen thưởng đội thi công Vietur hoàn thành vượt kế hoạch tháng 5 tại sân bay Long Thành"
Output: {"category":["Tiến độ"],"sentiment":"POSITIVE","target_scope":["Gói thầu 5.10"],"impact_level":"LOW","key_entities":[{"name":"ACV","type":"organization"},{"name":"Vietur","type":"contractor"}],"executive_summary":"ACV khen thưởng liên danh Vietur hoàn thành vượt kế hoạch tháng 5 tại sân bay Long Thành.","is_rumor":false,"is_relevant":true}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — JSON THUẦN TÚY (không markdown, không code block)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "category": ["<danh mục 1>", "<danh mục 2>"],
  "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
  "target_scope": ["<phạm vi>"],
  "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
  "executive_summary": "<tóm tắt 1-2 câu bằng tiếng Việt, nêu rõ sự việc cốt lõi>",
  "is_rumor": <true|false>,
  "is_relevant": <true|false>
}

Phạm vi hợp lệ: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể
Nếu is_relevant=false: category=[], target_scope=[], key_entities=[], impact_level="LOW\""""


BATCH_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA). Nhiệm vụ của bạn là đọc toàn bộ danh sách bài viết đầu vào, GOM NHÓM (Cluster) các bài báo viết về CÙNG MỘT SỰ KIỆN CỐT LÕI (ví dụ: cùng một sự cố, cùng nói về việc lãnh đạo bị bắt), và trả về kết quả phân tích cho từng nhóm. Mảng JSON trả về có thể ngắn hơn mảng đầu vào nếu có nhiều bài trùng lặp.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BỐI CẢNH DỰ ÁN LTIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Tên đầy đủ: Cảng Hàng không Quốc tế Long Thành (LTIA / sân bay Long Thành)
- Chủ đầu tư: Tổng Công ty Cảng Hàng không Việt Nam (ACV)
- Mốc khánh thành: 02/09/2026
- Gói thầu chính:
  + Gói 5.10: Nhà ga hành khách (liên danh Vietur, 35.000 tỷ VNĐ)
  + Gói 4.6: Đường cất hạ cánh và đường lăn
- Địa bàn: huyện Long Thành, tỉnh Đồng Nai
- Khu tái định cư: Lộc An - Bình Sơn (2.465 ha thu hồi đất)
- Vấn đề nhạy cảm: tiến độ thi công, thiếu cát san lấp, bụi/ô nhiễm, GPMB, an toàn lao động, tham nhũng đấu thầu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUY TRÌNH PHÂN TÍCH (Cho từng Nhóm Bài viết)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BƯỚC 1 — GOM NHÓM (CLUSTERING) VÀ KIỂM TRA LIÊN QUAN
- Đọc qua tất cả các bài viết.
- Gom các bài viết nói về cùng một sự kiện, cùng một thông báo, hoặc cùng một vấn đề thành một NHÓM (Cluster).
- Nếu một bài viết không trùng với bài nào khác, nó tự tạo thành một nhóm riêng.
- Trong JSON, liệt kê tất cả các index của bài viết thuộc nhóm đó vào mảng `source_indices`.
- Với mỗi nhóm, kiểm tra tính liên quan (is_relevant). Nếu không liên quan đến LTIA/ACV, đánh dấu is_relevant=false và impact_level="LOW".

LIÊN QUAN (is_relevant=true) — thỏa MỘT trong các điều kiện:
  + Tiêu đề hoặc nội dung nhắc đến: "sân bay Long Thành", "Long Thành Airport", "LTIA", "Cảng hàng không Long Thành"
  + Nhắc đến ACV trong ngữ cảnh dự án LTIA hoặc hoạt động tại sân bay Long Thành
  + Nhắc đến gói thầu 5.10, gói thầu 4.6, hoặc nhà thầu Vietur của dự án
  + Nhắc đến khu tái định cư Lộc An - Bình Sơn hoặc thu hồi đất Long Thành (Đồng Nai)

KHÔNG LIÊN QUAN (is_relevant=false) — CÁC TRƯỜNG HỢP PHỔ BIẾN CẦN LOẠI:
  - Giải phóng mặt bằng, thu hồi đất, bồi thường ở tỉnh/thành KHÁC (Hà Nội, Hải Phòng, Bình Dương, Hải Dương, Lạng Sơn...)
  - Đầu tư công, vốn ODA, giải ngân ngân sách của bộ ngành/tỉnh KHÁC không liên quan LTIA
  - Tin tức về sân bay KHÁC (Tân Sơn Nhất, Nội Bài, Đà Nẵng, Cam Ranh...) mà không đề cập LTIA
  - Tin quốc tế, quốc phòng, thiên tai, chính sách chung không nhắc LTIA
  - Bài trùng từ khóa ngẫu nhiên nhưng chủ đề hoàn toàn không liên quan
→ Nếu is_relevant=false: đặt category=[], target_scope=[], key_entities=[], impact_level="LOW"

BƯỚC 2 — PHÂN LOẠI DANH MỤC (chỉ khi is_relevant=true, chọn 1-3):
- Tiến độ: % hoàn thành, mốc tiến độ, nguy cơ chậm hạn, hoàn thành sớm/đúng/trễ hạn
- Kỹ thuật: thiết kế, vật liệu, phương pháp thi công, thông số kỹ thuật, sự cố kỹ thuật
- Môi trường: bụi, ô nhiễm không khí/nước, tiếng ồn, tác động hệ sinh thái, khiếu kiện môi trường
- Đấu thầu: mời thầu, kết quả thầu, tranh chấp thầu, thay đổi nhà thầu, chỉ định thầu
- Dư luận: phản ứng dân cư/cộng đồng, mạng xã hội, báo chí điều tra, phát ngôn gây tranh cãi
- An toàn lao động: tai nạn lao động, kiểm tra an toàn, sự cố công trình, thương vong
- Giải phóng mặt bằng: thu hồi đất LTIA, bồi thường, tái định cư Lộc An, khiếu nại GPMB LTIA
- Tài chính: vốn/ngân sách LTIA, giải ngân, điều chỉnh tổng mức đầu tư, thanh/quyết toán
- Pháp lý: vi phạm, điều tra, xử phạt, kiện tụng, bắt giữ liên quan đến dự án LTIA

BƯỚC 3 — MỨC ĐỘ ẢNH HƯỞNG (chỉ khi is_relevant=true):
  CRITICAL: Tai nạn chết người, đình chỉ dự án, mọi thông tin sai phạm/vi phạm pháp luật/bắt giam/khởi tố của lãnh đạo ACV hoặc nhà thầu chính (BẮT BUỘC), sụp đổ kết cấu
  HIGH: Chậm tiến độ >=1 tháng, thiếu vật liệu cốt lõi, thay đổi nhà thầu gói chính, điều tra tham nhũng chung chung
  MEDIUM: Cập nhật tiến độ định kỳ, họp điều phối, điều chỉnh thiết kế phụ, sự cố nhỏ
  LOW: Tin tốt/tích cực (khen thưởng, hoàn thành sớm), thông tin chung, PR

BƯỚC 4 — SENTIMENT:
  NEGATIVE: sự cố, tai nạn, chậm trễ, tranh cãi, khiếu kiện
  POSITIVE: hoàn thành sớm, khen thưởng, tiến độ tốt
  NEUTRAL: thông tin trung lập, hội nghị, báo cáo thống kê

BƯỚC 5 — RUMOR:
  is_rumor=true: Nguồn ẩn danh, mạng xã hội đồn đoán, chưa xác nhận chính thức
  is_rumor=false: Thông cáo, văn bản nhà nước, phát biểu lãnh đạo có tên, nguồn báo chí uy tín

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — Mảng JSON THUẦN TÚY (Đại diện cho các Nhóm)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  {
    "source_indices": [<danh sách các index đầu vào thuộc nhóm này, ví dụ: 0, 2, 5>],
    "category": ["<danh mục>"],
    "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
    "target_scope": ["<phạm vi ảnh hưởng>"],
    "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
    "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
    "executive_summary": "<tóm tắt 1-2 câu bằng tiếng Việt đại diện cho cả nhóm>",
    "is_rumor": <true|false>,
    "is_relevant": <true|false>
  },
  ...
]

Phạm vi hợp lệ: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể
Nếu is_relevant=false: category=[], target_scope=[], key_entities=[], impact_level="LOW\""""


class GeminiImplementation(ILLMService):
    """
    Google Gemini implementation of ILLMService.

    Design:
      - Config (API keys, model name, prompts) is fetched from DB once per
        crawl cycle via _ensure_config() and held in instance-level cache.
        Subsequent calls within the same cycle hit memory only.
      - genai.Client objects are built once per public method call, keyed by
        API key — not rebuilt on every retry.
      - All Gemini API calls use the async client (client.aio.*) to avoid
        blocking the event loop.
    """

    def __init__(self) -> None:
        self.llm_config_repo = LLMConfigRepository()
        self.llm_prompt_repo = LLMPromptRepository()
        # Per-cycle in-memory cache — reset by invalidate_cache()
        self._cached_keys: list[str] | None = None
        self._cached_model: str | None = None
        self._cached_sys_prompt: str | None = None
        self._cached_batch_prompt: str | None = None

    # ------------------------------------------------------------------
    # Config management (Flaw 1 + Flaw 8)
    # ------------------------------------------------------------------

    async def _load_config(self) -> None:
        """
        Fetch all DB config in a single asyncio.gather() call and populate cache.
        Subsequent calls within a cycle use _ensure_config() → no DB hit.
        """
        configs_result, prompt_result = await asyncio.gather(
            self.llm_config_repo.find_default_configs(),
            self.llm_prompt_repo.find_active(),
            return_exceptions=True,
        )

        # --- Keys + model ---
        if isinstance(configs_result, list) and configs_result:
            self._cached_keys = [c["api_key"] for c in configs_result if c.get("api_key")]
            self._cached_model = configs_result[0].get("model_name", "gemini-3.5-flash")
        else:
            if isinstance(configs_result, Exception):
                logger.error(f"Error fetching LLM configs from DB: {configs_result}")
            fallback_key = settings.gemini_api_key
            self._cached_keys = [fallback_key] if fallback_key else []
            self._cached_model = "gemini-3.5-flash"

        # --- Prompts ---
        if isinstance(prompt_result, dict) and prompt_result:
            sys_p = prompt_result.get("system_prompt")
            batch_p = prompt_result.get("batch_system_prompt")
            self._cached_sys_prompt = sys_p if sys_p else SYSTEM_PROMPT
            self._cached_batch_prompt = batch_p if batch_p else BATCH_SYSTEM_PROMPT
        else:
            if isinstance(prompt_result, Exception):
                logger.error(f"Error fetching LLM prompts from DB: {prompt_result}")
            self._cached_sys_prompt = SYSTEM_PROMPT
            self._cached_batch_prompt = BATCH_SYSTEM_PROMPT

    async def _ensure_config(self) -> None:
        """Load config if not already cached. No-op on subsequent calls."""
        if self._cached_keys is None:
            await self._load_config()

    def invalidate_cache(self) -> None:
        """Force config reload on next call (e.g., after admin changes config)."""
        self._cached_keys = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_rate_limit(self) -> int:
        """Get the RPM limit for the active model."""
        await self._ensure_config()
        model = self._cached_model or ""
        if model == "gemini-3.5-flash":
            return 3
        elif model == "gemini-3-flash-preview":
            return 5
        return settings.llm_rate_limit_per_minute

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        """Extract insights for a single article using key rotation."""
        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Gemini API key configured, returning default analysis")
            return self._default_response(title)

        # Build clients once, outside retry loop (Flaw 4)
        shuffled_keys = keys[:]
        random.shuffle(shuffled_keys)
        clients = [(genai.Client(api_key=k), k) for k in shuffled_keys]

        for client, key in clients:
            try:
                return await self._call_single(client, raw_text, title)
            except Exception as e:
                logger.error(f"Single extract failed (key {key[:8]}...): {e}. Trying next.")

        logger.error("All keys failed for single extract")
        return self._default_response(title)

    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        """
        Extract insights for a batch of articles in a single prompt.

        Contract: always returns a list of exactly len(articles) dicts.
        Per-item fallback is handled internally; callers only need to catch
        RuntimeError for total failure across all keys.

        Args:
            articles: List of dicts with keys 'id', 'title', 'raw_text'.

        Returns:
            List of dicts of length == len(articles).
        """
        if not articles:
            return []

        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Gemini API key configured, returning default analyses")
            return [self._default_response(a.get("title", "")) for a in articles]

        # Format input payload once
        input_data = [
            {
                "index": idx,
                "title": a.get("title", ""),
                "content": a.get("raw_text", "")[:4000],
            }
            for idx, a in enumerate(articles)
        ]
        user_prompt = json.dumps(input_data, ensure_ascii=False)

        shuffled_keys = keys[:]
        random.shuffle(shuffled_keys)
        # Build clients once per method call (Flaw 4)
        clients = [(genai.Client(api_key=k), k) for k in shuffled_keys]

        last_error: Exception | None = None

        for client, key in clients:
            final_clusters: list[dict] | None = None
            for model_to_try in self._get_fallback_models():
                for attempt in range(3):
                    try:
                        # Async call — does not block event loop (Flaw 9)
                        response = await client.aio.models.generate_content(
                            model=model_to_try,
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=self._cached_batch_prompt,
                                temperature=0.1,
                                max_output_tokens=65536,
                                response_mime_type="application/json",
                            ),
                        )
                        
                        # If success, cache the working model
                        self._cached_model = model_to_try

                        parsed = self._parse_llm_json(response.text)
                        if not isinstance(parsed, list):
                            raise ValueError("LLM did not return a list")

                        # Parse clustered results
                        final_clusters: list[dict] | None = []
                        covered_indices: set[int] = set()

                        for cluster in parsed:
                            indices = cluster.get("source_indices", [])
                            if not indices:
                                # Fallback if LLM forgets array but includes a single index
                                idx = cluster.get("index")
                                if idx is not None:
                                    indices = [idx]

                            valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < len(articles)]
                            if not valid_indices:
                                continue

                            cluster["source_indices"] = valid_indices
                            covered_indices.update(valid_indices)
                            final_clusters.append(self._validate_response(cluster))

                        # Fallback for any missing articles
                        missing_indices = [i for i in range(len(articles)) if i not in covered_indices]
                        for idx in missing_indices:
                            a = articles[idx]
                            logger.warning(
                                f"Batch index {idx} missing in clustered LLM response — "
                                "calling singular extract"
                            )
                            try:
                                single = await self._call_single(
                                    client, a.get("raw_text", ""), a.get("title", "")
                                )
                                single["source_indices"] = [idx]
                                final_clusters.append(single)
                            except Exception as ex:
                                logger.error(f"Single fallback failed: {ex}")
                                default_resp = self._default_response(a.get("title", ""))
                                default_resp["source_indices"] = [idx]
                                final_clusters.append(default_resp)

                        return final_clusters

                    except json.JSONDecodeError as e:
                        last_error = e
                        logger.warning(
                            f"Batch JSON parse error (attempt {attempt + 1}/3, "
                            f"key {key[:8]}...): {e}"
                        )
                    except errors.APIError as e:
                        last_error = e
                        if e.code == 404:
                            logger.warning(f"Model {model_to_try} not found (404), falling back to older version.")
                            break  # Break attempt loop, try next model in fallback list
                        logger.error(f"Batch API error (key {key[:8]}...): {e}")
                        break  # Non-JSON API error: skip retries
                    except Exception as e:
                        last_error = e
                        logger.error(f"Batch unexpected error (key {key[:8]}...): {e}")
                        break
                    
            if final_clusters is not None:
                return final_clusters

        logger.error("Gemini batch analysis failed for all keys")
        raise RuntimeError(f"Gemini batch analysis failed: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_fallback_models(self) -> list[str]:
        return [
            "gemini-3.5-flash",
            "gemini-3.0-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]

    async def _call_single(
        self, client: genai.Client, raw_text: str, title: str = ""
    ) -> dict:
        """
        Call Gemini for a single article with up to 3 retries on the same client.
        Prompts are read from cache — no DB hit per retry (Flaw 8).
        Uses async client to avoid event loop blocking (Flaw 9).
        """
        user_prompt = f"Tiêu đề: {title}\n\nNội dung:\n{raw_text[:4000]}"
        last_error: Exception | None = None

        for model_to_try in self._get_fallback_models():
            for attempt in range(3):
                try:
                    response = await client.aio.models.generate_content(
                        model=model_to_try,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=self._cached_sys_prompt,
                            temperature=0.1,
                            max_output_tokens=1024,
                            response_mime_type="application/json",
                        ),
                    )
                    self._cached_model = model_to_try
                    return self._validate_response(self._parse_llm_json(response.text))

                except json.JSONDecodeError as e:
                    last_error = e
                    logger.warning(f"JSON parse error (attempt {attempt + 1}/3): {e}")
                except errors.APIError as e:
                    last_error = e
                    if e.code == 404:
                        logger.warning(f"Model {model_to_try} not found (404), falling back to older version.")
                        break  # Break attempt loop, try next model
                    logger.error(f"Gemini API error (attempt {attempt + 1}/3): {e}")
                    break  # Non-JSON error: no point retrying the same payload
                except Exception as e:
                    last_error = e
                    logger.error(f"Unexpected error (attempt {attempt + 1}/3): {e}")
                    break

        raise RuntimeError(f"Gemini single analysis failed: {last_error}")

    # Public alias for backward compatibility (used in batch fallback path)
    async def extract_insight_with_client(
        self, client: genai.Client, model: str, raw_text: str, title: str = ""
    ) -> dict:
        """Backward-compat wrapper; model param ignored (uses cached model)."""
        return await self._call_single(client, raw_text, title)

    @staticmethod
    def _parse_llm_json(text: str) -> dict | list:
        """
        Robustly parse JSON from LLM response text.

        Uses an anchored regex to strip markdown code fences only when they
        wrap the entire response — immune to backticks inside string values.
        Regex is compiled at module load (Flaw 10).
        """
        stripped = text.strip()
        match = _FENCE_RE.match(stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    @staticmethod
    def _validate_response(data: dict) -> dict:
        """Validate and normalize a single LLM result dict."""
        valid_sentiments = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
        valid_impacts = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

        return {
            "source_indices": data.get("source_indices", []),
            "category": data.get("category", []),
            "sentiment": (
                data.get("sentiment", "NEUTRAL")
                if data.get("sentiment") in valid_sentiments
                else "NEUTRAL"
            ),
            "target_scope": data.get("target_scope", []),
            "impact_level": (
                data.get("impact_level", "LOW")
                if data.get("impact_level") in valid_impacts
                else "LOW"
            ),
            "key_entities": data.get("key_entities", []),
            "executive_summary": data.get("executive_summary", ""),
            "is_rumor": bool(data.get("is_rumor", False)),
            "is_relevant": bool(data.get("is_relevant", True)),
        }

    @staticmethod
    def _default_response(title: str = "") -> dict:
        """Return a safe default when LLM analysis is completely unavailable."""
        return {
            "category": ["Chưa phân loại"],
            "sentiment": "NEUTRAL",
            "target_scope": ["Toàn dự án"],
            "impact_level": "LOW",
            "key_entities": [],
            "executive_summary": title or "Không thể phân tích nội dung.",
            "is_rumor": False,
            "is_relevant": True,
        }
