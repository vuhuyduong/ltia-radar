"""
IAlertService — Abstract interface for alert/notification delivery.
"""

from abc import ABC, abstractmethod

from app.domain.entities.processed_data import ProcessedData
from app.domain.entities.alert_rule import AlertRule


class IAlertService(ABC):
    """
    Alert delivery interface.
    Concrete implementations (Telegram, Email, Slack) live in Infrastructure Layer.
    """

    @abstractmethod
    async def send_alert(
        self, processed_data: ProcessedData, rule: AlertRule
    ) -> bool:
        """
        Send an alert notification for a processed article that matched a rule.

        Args:
            processed_data: The AI-analyzed article data.
            rule: The alert rule that was triggered.

        Returns:
            True if alert was sent successfully, False otherwise.
        """
        pass
