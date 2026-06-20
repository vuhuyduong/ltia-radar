import logging

from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import LLMConfigRepository

logger = logging.getLogger(__name__)

class DynamicLLMService(ILLMService):
    def __init__(self):
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

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        gemini_service = self._get_gemini()
        try:
            return await gemini_service.extract_insight(raw_text, title)
        except Exception as e:
            logger.warning(f"Gemini single extract failed ({e}). Falling back to Groq...")
            groq_service = self._get_groq()
            return await groq_service.extract_insight(raw_text, title)
            
    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        gemini_service = self._get_gemini()
        try:
            return await gemini_service.extract_insights_batch(articles)
        except Exception as e:
            logger.warning(f"Gemini batch extract failed ({e}). Falling back to Groq...")
            groq_service = self._get_groq()
            return await groq_service.extract_insights_batch(articles)
