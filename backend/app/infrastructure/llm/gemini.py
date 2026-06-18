"""
GeminiImplementation — Concrete LLM service using Google Gemini 2.5 Flash.
Implements ILLMService interface (PRD Section 9.1).
"""

import json
import logging

from google import genai
from google.genai import types

from app.config import settings
from app.domain.interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)

# System prompt designed specifically for LTIA domain analysis
SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA).

Nhiệm vụ: Phân tích bài viết báo chí/mạng xã hội và trích xuất thông tin có cấu trúc.

BỐI CẢNH DỰ ÁN:
- Dự án sân bay Long Thành là siêu dự án trọng điểm quốc gia, mốc khánh thành 01/12/2026
- Các gói thầu quan trọng: Gói 5.10 (Nhà ga, Vietur, 35.000 tỷ), Gói 4.6 (Đường cất hạ cánh)
- Chủ đầu tư: Tổng Công ty Cảng hàng không Việt Nam (ACV)
- Các vấn đề nhạy cảm: tiến độ, bụi/ô nhiễm, giải phóng mặt bằng, thiếu vật liệu, an toàn lao động
- Diện tích thu hồi đất: 2.465 ha tại Long Thành, Nhơn Trạch

QUY TẮC PHÂN TÍCH:
1. CRITICAL: Sự cố nghiêm trọng (tai nạn, đình chỉ, xử phạt, đình công), bài trên báo lớn phản ánh sai phạm
2. HIGH: Vấn đề ảnh hưởng tiến độ (thiếu vật liệu, chậm giải ngân, thay đổi nhà thầu)
3. MEDIUM: Thông tin dự án cần theo dõi (cập nhật tiến độ, hội nghị, điều chỉnh kỹ thuật)
4. LOW: Tin tức thông thường, quảng bá tích cực
5. is_rumor=true: Khi bài viết chứa thông tin chưa xác minh, nguồn ẩn danh, hoặc mang tính đồn đại

Trả về JSON thuần túy (không markdown, không code block) với cấu trúc sau:
{
  "category": ["<danh mục>"],
  "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
  "target_scope": ["<phạm vi ảnh hưởng>"],
  "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
  "executive_summary": "<tóm tắt 1-2 câu cốt lõi sự việc>",
  "is_rumor": <true|false>
}

Danh mục hợp lệ: Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận, An toàn lao động, Giải phóng mặt bằng, Tài chính, Pháp lý
Phạm vi: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể"""


class GeminiImplementation(ILLMService):
    """Google Gemini 2.5 Flash implementation of ILLMService."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        self.model = "gemini-2.5-flash"

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        """
        Send article text to Gemini for analysis.
        Implements retry logic: max 2 retries on JSON parse error (US-3.1).
        """
        if not self.api_key:
            logger.warning("Gemini API key not configured, returning default analysis")
            return self._default_response(title)

        user_prompt = f"Tiêu đề: {title}\n\nNội dung:\n{raw_text[:15000]}"

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        max_output_tokens=1024,
                    ),
                )

                result_text = response.text.strip()

                # Clean markdown code fences if present
                if result_text.startswith("```"):
                    result_text = result_text.split("\n", 1)[1]
                if result_text.endswith("```"):
                    result_text = result_text.rsplit("```", 1)[0]
                result_text = result_text.strip()

                parsed = json.loads(result_text)
                return self._validate_response(parsed)

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    f"Gemini JSON parse error (attempt {attempt + 1}/{max_retries}): {e}"
                )
            except Exception as e:
                last_error = e
                logger.error(f"Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    break

        # All retries failed — return default with error logged
        logger.error(f"Gemini analysis failed after {max_retries} attempts: {last_error}")
        return self._default_response(title)

    def _validate_response(self, data: dict) -> dict:
        """Validate and normalize the LLM response."""
        valid_sentiments = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
        valid_impacts = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

        return {
            "category": data.get("category", []),
            "sentiment": data.get("sentiment", "NEUTRAL")
                if data.get("sentiment") in valid_sentiments else "NEUTRAL",
            "target_scope": data.get("target_scope", []),
            "impact_level": data.get("impact_level", "LOW")
                if data.get("impact_level") in valid_impacts else "LOW",
            "key_entities": data.get("key_entities", []),
            "executive_summary": data.get("executive_summary", ""),
            "is_rumor": bool(data.get("is_rumor", False)),
        }

    def _default_response(self, title: str = "") -> dict:
        """Return a safe default when LLM analysis fails."""
        return {
            "category": ["Chưa phân loại"],
            "sentiment": "NEUTRAL",
            "target_scope": ["Toàn dự án"],
            "impact_level": "LOW",
            "key_entities": [],
            "executive_summary": title or "Không thể phân tích nội dung.",
            "is_rumor": False,
        }
