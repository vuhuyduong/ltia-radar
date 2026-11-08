import logging

from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import LLMConfigRepository
from app.infrastructure.llm.quota import QuotaExhausted

logger = logging.getLogger(__name__)


class DynamicLLMService(ILLMService):
    """
    Primary LLM service using Google Gemini (`gemini-3.8-flash`, effort high).
    Falls back to Groq ONLY if active Groq API keys are actually configured in DB;
    otherwise re-raises the error so the caller does not silently write fake
    default articles to `processed_data`.
    """

    def __init__(self) -> None:
        self.llm_config_repo = LLMConfigRepository()
        self._gemini: ILLMService | None = None
        self._groq: ILLMService | None = None

    def _get_gemini(self) -> ILLMService:
        if not self._gemini:
            from app.infrastructure.llm.gemini import GeminiImplementation
            self._gemini = GeminiImplementation()
        return self._gemini

    def _get_groq(self) -> ILLMService:
        if not self._groq:
            from app.infrastructure.llm.groq_llm import GroqImplementation
            self._groq = GroqImplementation()
        return self._groq

    async def get_rate_limit(self) -> int:
        return await self._get_gemini().get_rate_limit()

    def start_run_tracking(self) -> None:
        self._get_gemini().start_run_tracking()
        if self._groq:
            self._groq.start_run_tracking()

    async def get_run_metrics(self) -> dict:
        if self._groq and getattr(self._groq, "_run_calls_count", 0) > 0:
            return await self._groq.get_run_metrics()
        return await self._get_gemini().get_run_metrics()

    async def _has_groq_keys(self) -> bool:
        groq_service = self._get_groq()
        await groq_service._ensure_config()  # type: ignore[attr-defined]
        return bool(getattr(groq_service, "_cached_keys", None))

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        gemini_service = self._get_gemini()
        try:
            return await gemini_service.extract_insight(raw_text, title)
        except Exception as e:
            if await self._has_groq_keys():
                logger.warning(f"Gemini single extract failed ({e}). Falling back to Groq...")
                return await self._get_groq().extract_insight(raw_text, title)
            raise

    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        gemini_service = self._get_gemini()
        try:
            return await gemini_service.extract_insights_batch(articles)
        except QuotaExhausted as qe:
            if await self._has_groq_keys():
                logger.warning(f"Gemini quota exhausted ({qe}). Falling back to Groq...")
                return await self._get_groq().extract_insights_batch(articles)
            raise
        except Exception as e:
            if await self._has_groq_keys():
                logger.warning(f"Gemini batch extract failed ({e}). Falling back to Groq...")
                return await self._get_groq().extract_insights_batch(articles)
            raise
