"""
ILLMService — Abstract interface for LLM-based text analysis.
Following Clean Architecture / Dependency Inversion Principle (PRD Section 9.1).
"""

from abc import ABC, abstractmethod


class ILLMService(ABC):
    """
    Core NLP processing interface.
    The Application Layer only works with this interface.
    Concrete implementations (Gemini, OpenAI, Local LLM) live in Infrastructure Layer.
    """

    @abstractmethod
    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        """
        Analyze raw article text and return structured insights.
        """
        pass

    @abstractmethod
    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        """
        Analyze a batch of raw articles and return structured insights for each.
        
        Args:
            articles: List of dicts containing 'title' and 'raw_text'.
            
        Returns:
            List of dicts representing structured insights.
        """
        pass

    async def get_rate_limit(self) -> int:
        """
        Get the rate limit (RPM) of the active model configuration.
        """
        return 10


