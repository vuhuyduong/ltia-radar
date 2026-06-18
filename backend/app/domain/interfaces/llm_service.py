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

        Args:
            raw_text: Full article text content.
            title: Article title for additional context.

        Returns:
            Dictionary containing:
            - category: list[str]
            - sentiment: str (POSITIVE/NEGATIVE/NEUTRAL)
            - target_scope: list[str]
            - impact_level: str (CRITICAL/HIGH/MEDIUM/LOW)
            - key_entities: list[dict]
            - executive_summary: str
            - is_rumor: bool
        """
        pass
