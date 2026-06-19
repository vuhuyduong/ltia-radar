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
from google.genai import types

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

SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA).

Nhiệm vụ: Phân tích bài viết báo chí/mạng xã hội và trích xuất thông tin có cấu trúc.

BỐI CẢNH DỰ ÁN:
- Dự án sân bay Long Thành là siêu dự án trọng điểm quốc gia, mốc khánh thành 01/12/2026
- Các gói thầu quan trọng: Gói 5.10 (Nhà ga, Vietur, 35.000 tỷ), Gói 4.6 (Đường cất hạ cánh)
- Chủ đầu tư: Tổng Công ty Cảng hàng không Việt Nam (ACV)
- Các vấn đề nhạy cảm: tiến độ, bụi/ô nhiễm, giải phóng mặt bằng, thiếu vật liệu, an toàn lao động
- Diện tích thu hồi đất: 2.465 ha tại Long Thành, Nhơn Trạch

QUY TẮC PHÂN TÍCH:
1. CRITICAL: Sự cố nghiêm trọng (tai nạn chết người, đình chỉ dự án, xử phạt pháp lý nặng, đình công quy mô lớn), bài viết phản ánh sai phạm lớn của lãnh đạo ACV hoặc nhà thầu.
2. HIGH: Vấn đề ảnh hưởng tiến độ thi công (thiếu cát san lấp, chậm giải ngân vốn đầu tư công trực tiếp cho dự án, chậm bàn giao mặt bằng thi công, thay đổi nhà thầu gói thầu chính).
3. MEDIUM: Thông tin dự án cần theo dõi (cập nhật tiến độ hàng tuần, hội nghị điều phối dự án, điều chỉnh thông số kỹ thuật phụ).
4. LOW: Tin tức thông thường hoặc quảng bá tích cực (hình ảnh tiến độ đẹp, khen thưởng, ký kết hợp tác thương mại thông thường).
5. is_rumor=true: Khi bài viết chứa thông tin chưa xác minh, nguồn ẩn danh, mạng xã hội đồn đoán chưa được báo chí chính thống đăng tải.
6. is_relevant=true/false (QUY TẮC RẤT NGHIÊM NGẶT - TRÁNH TIN RÁC):
   - Đặt là true NẾU VÀ CHỈ NẾU bài viết trực tiếp nhắc đến Dự án Cảng Hàng không Quốc tế Long Thành (sân bay Long Thành), Tổng Công ty Cảng hàng không Việt Nam (ACV), hoặc các gói thầu, nhân sự lãnh đạo, dự án/hoạt động hàng không trực thuộc ACV.
   - BẮT BUỘC đặt là false nếu bài viết chỉ trùng từ khóa chung nhưng nói về địa phương khác hoặc dự án khác không liên quan đến sân bay Long Thành (Ví dụ: bồi thường giải phóng mặt bằng ở Hà Nội, Hải Dương, Lạng Sơn; tin thời sự chung quốc tế, quốc phòng; tình hình giải ngân đầu tư công của các bộ ngành khác).
   - Nếu bài viết KHÔNG nhắc đến "Long Thành", "sân bay Long Thành" hoặc "ACV" trong tiêu đề hay nội dung cốt lõi, hãy đặt is_relevant = false.

Trả về JSON thuần túy (không markdown, không code block) với cấu trúc sau:
{
  "category": ["<danh mục>"],
  "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
  "target_scope": ["<phạm vi ảnh hưởng>"],
  "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
  "executive_summary": "<tóm tắt 1-2 câu cốt lõi sự việc>",
  "is_rumor": <true|false>,
  "is_relevant": <true|false>
}

Danh mục hợp lệ: Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận, An toàn lao động, Giải phóng mặt bằng, Tài chính, Pháp lý
Phạm vi: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể"""


BATCH_SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA).

Nhiệm vụ: Phân tích danh sách các bài viết báo chí/mạng xã hội và trích xuất thông tin có cấu trúc cho từng bài viết.

BỐI CẢNH DỰ ÁN:
- Dự án sân bay Long Thành là siêu dự án trọng điểm quốc gia, mốc khánh thành 01/12/2026
- Các gói thầu quan trọng: Gói 5.10 (Nhà ga, Vietur, 35.000 tỷ), Gói 4.6 (Đường cất hạ cánh)
- Chủ đầu tư: Tổng Công ty Cảng hàng không Việt Nam (ACV)
- Các vấn đề nhạy cảm: tiến độ, bụi/ô nhiễm, giải phóng mặt bằng, thiếu vật liệu, an toàn lao động
- Diện tích thu hồi đất: 2.465 ha tại Long Thành, Nhơn Trạch

QUY TẮC PHÂN TÍCH:
1. CRITICAL: Sự cố nghiêm trọng (tai nạn chết người, đình chỉ dự án, xử phạt pháp lý nặng, đình công quy mô lớn), bài viết phản ánh sai phạm lớn của lãnh đạo ACV hoặc nhà thầu.
2. HIGH: Vấn đề ảnh hưởng tiến độ thi công (thiếu cát san lấp, chậm giải ngân vốn đầu tư công trực tiếp cho dự án, chậm bàn giao mặt bằng thi công, thay đổi nhà thầu gói thầu chính).
3. MEDIUM: Thông tin dự án cần theo dõi (cập nhật tiến độ hàng tuần, hội nghị điều phối dự án, điều chỉnh thông số kỹ thuật phụ).
4. LOW: Tin tức thông thường hoặc quảng bá tích cực (hình ảnh tiến độ đẹp, khen thưởng, ký kết hợp tác thương mại thông thường).
5. is_rumor=true: Khi bài viết chứa thông tin chưa xác minh, nguồn ẩn danh, mạng xã hội đồn đoán chưa được báo chí chính thống đăng tải.
6. is_relevant=true/false (QUY TẮC RẤT NGHIÊM NGẶT - TRÁNH TIN RÁC):
   - Đặt là true NẾU VÀ CHỈ NẾU bài viết trực tiếp nhắc đến Dự án Cảng Hàng không Quốc tế Long Thành (sân bay Long Thành), Tổng Công ty Cảng hàng không Việt Nam (ACV), hoặc các gói thầu, nhân sự lãnh đạo, dự án/hoạt động hàng không trực thuộc ACV.
   - BẮT BUỘC đặt là false nếu bài viết chỉ trùng từ khóa chung nhưng nói về địa phương khác hoặc dự án khác không liên quan đến sân bay Long Thành (Ví dụ: bồi thường giải phóng mặt bằng ở Hà Nội, Hải Dương, Lạng Sơn; tin thời sự chung quốc tế, quốc phòng; tình hình giải ngân đầu tư công của các bộ ngành khác).
   - Nếu bài viết KHÔNG nhắc đến "Long Thành", "sân bay Long Thành" hoặc "ACV" trong tiêu đề hay nội dung cốt lõi, hãy đặt is_relevant = false.

Trả về mảng JSON thuần túy (không markdown, không code block) đại diện cho kết quả phân tích tương ứng của từng bài viết trong mảng đầu vào, theo đúng thứ tự:
[
  {
    "index": <số thứ tự tương ứng, từ 0>,
    "category": ["<danh mục>"],
    "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
    "target_scope": ["<phạm vi ảnh hưởng>"],
    "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
    "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
    "executive_summary": "<tóm tắt 1-2 câu cốt lõi sự việc>",
    "is_rumor": <true|false>,
    "is_relevant": <true|false>
  },
  ...
]

Danh mục hợp lệ: Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận, An toàn lao động, Giải phóng mặt bằng, Tài chính, Pháp lý
Phạm vi: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể"""


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
            for attempt in range(3):
                try:
                    # Async call — does not block event loop (Flaw 9)
                    response = await client.aio.models.generate_content(
                        model=self._cached_model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=self._cached_batch_prompt,
                            temperature=0.1,
                            max_output_tokens=4096,
                            response_mime_type="application/json",
                        ),
                    )

                    parsed = self._parse_llm_json(response.text)
                    if not isinstance(parsed, list):
                        raise ValueError("LLM did not return a list")

                    # Map by index; fill gaps with per-item fallback
                    results_map: dict[int, dict] = {
                        item.get("index"): item
                        for item in parsed
                        if "index" in item
                    }

                    final: list[dict] = []
                    for idx, a in enumerate(articles):
                        item = results_map.get(idx)
                        if item:
                            final.append(self._validate_response(item))
                        else:
                            logger.warning(
                                f"Batch index {idx} missing in LLM response — "
                                "calling singular extract"
                            )
                            try:
                                single = await self._call_single(
                                    client, a.get("raw_text", ""), a.get("title", "")
                                )
                                final.append(single)
                            except Exception as ex:
                                logger.error(f"Single fallback failed: {ex}")
                                final.append(self._default_response(a.get("title", "")))

                    return final

                except json.JSONDecodeError as e:
                    last_error = e
                    logger.warning(
                        f"Batch JSON parse error (attempt {attempt + 1}/3, "
                        f"key {key[:8]}...): {e}"
                    )
                except Exception as e:
                    last_error = e
                    logger.error(f"Batch API error (key {key[:8]}...): {e}")
                    break  # Non-JSON error: skip retries, try next key

        logger.error("Gemini batch analysis failed for all keys")
        raise RuntimeError(f"Gemini batch analysis failed: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

        for attempt in range(3):
            try:
                response = await client.aio.models.generate_content(
                    model=self._cached_model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self._cached_sys_prompt,
                        temperature=0.1,
                        max_output_tokens=1024,
                        response_mime_type="application/json",
                    ),
                )
                return self._validate_response(self._parse_llm_json(response.text))

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parse error (attempt {attempt + 1}/3): {e}")
            except Exception as e:
                last_error = e
                logger.error(f"Gemini API error (attempt {attempt + 1}/3): {e}")
                break  # Non-JSON error: no point retrying the same payload

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
