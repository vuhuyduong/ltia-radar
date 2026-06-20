"""
TelegramAlertService — Sends alert notifications via Telegram Bot API.
Implements IAlertService interface.
"""

import logging

import httpx

from app.config import settings
from app.domain.entities.alert_rule import AlertRule
from app.domain.entities.processed_data import ProcessedData
from app.domain.interfaces.alert_service import IAlertService

logger = logging.getLogger(__name__)

# Emoji indicators for impact levels
IMPACT_EMOJI = {
    "CRITICAL": "🔴🚨",
    "HIGH": "🟠⚠️",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}

SENTIMENT_EMOJI = {
    "NEGATIVE": "👎",
    "POSITIVE": "👍",
    "NEUTRAL": "➖",
}


class TelegramAlertService(IAlertService):
    """Telegram Bot API implementation of IAlertService."""

    def __init__(self, bot_token: str | None = None):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_alert(
        self, processed_data: ProcessedData, rule: AlertRule
    ) -> bool:
        """
        Send a formatted Telegram message for a triggered alert.

        Args:
            processed_data: The AI-analyzed article that triggered the rule.
            rule: The alert rule that was matched.

        Returns:
            True if message sent successfully.
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured, skipping alert")
            return False

        chat_id = rule.telegram_chat_id
        if not chat_id or chat_id == "default_chat_id":
            chat_id = settings.telegram_chat_id

        message = self._format_message(processed_data, rule)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False,
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        f"✅ Telegram alert sent to {chat_id}: "
                        f"{processed_data.impact_level} - {processed_data.title[:50]}"
                    )
                    return True
                else:
                    logger.error(
                        f"❌ Telegram API error {response.status_code}: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
            return False

    async def send_test_message(self, chat_id: str) -> bool:
        """Send a test message to verify Telegram configuration."""
        if not self.bot_token:
            return False

        if not chat_id or chat_id == "default_chat_id":
            chat_id = settings.telegram_chat_id

        test_message = (
            "🧪 <b>LTIA RADAR — TEST ALERT</b>\n\n"
            "✅ Cấu hình Telegram hoạt động bình thường!\n"
            "Hệ thống sẽ gửi cảnh báo qua kênh này khi phát hiện "
            "tin tức khớp với quy tắc đã thiết lập."
        )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": test_message,
                        "parse_mode": "HTML",
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return False

    def _format_message(
        self, processed_data: ProcessedData, rule: AlertRule
    ) -> str:
        """Format a rich Telegram alert message with HTML markup."""
        # Helper to clean Enum values from potential class prefix representation
        def clean_enum_value(val) -> str:
            if not val:
                return ""
            s = getattr(val, "value", str(val))
            if isinstance(s, str) and "." in s:
                s = s.split(".")[-1]
            return str(s).upper()

        impact_key = clean_enum_value(processed_data.impact_level)
        sentiment_key = clean_enum_value(processed_data.sentiment)

        # Mapping for display
        impact_display = {
            "CRITICAL": "Khẩn cấp (CRITICAL)",
            "HIGH": "Cao (HIGH)",
            "MEDIUM": "Trung bình (MEDIUM)",
            "LOW": "Thấp (LOW)",
        }.get(impact_key, impact_key)

        sentiment_display = {
            "NEGATIVE": "Tiêu cực (NEGATIVE)",
            "POSITIVE": "Tích cực (POSITIVE)",
            "NEUTRAL": "Trung lập (NEUTRAL)",
        }.get(sentiment_key, sentiment_key)

        impact_emoji = IMPACT_EMOJI.get(impact_key, "")
        sentiment_emoji = SENTIMENT_EMOJI.get(sentiment_key, "")

        # Categories
        categories = ", ".join(processed_data.category) if processed_data.category else "N/A"

        # Scope
        scope = ", ".join(processed_data.target_scope) if processed_data.target_scope else "Toàn dự án"

        # Key entities
        entities = ""
        if processed_data.key_entities:
            entity_names = [
                e.name if hasattr(e, "name") else e.get("name", "")
                for e in processed_data.key_entities
            ]
            entities = ", ".join(entity_names)

        # Rumor flag
        rumor_flag = "\n⚠️ <b>CẢNH BÁO TIN ĐỒN</b> — Cần xác minh!" if processed_data.is_rumor else ""

        message = (
            f"{impact_emoji} <b>LTIA RADAR — CẢNH BÁO {impact_key}</b>\n"
            f"{'━' * 30}\n\n"
            f"📰 <b>{processed_data.title}</b>\n\n"
            f"📝 <i>{processed_data.executive_summary}</i>\n\n"
            f"📊 Mức độ: <b>{impact_display}</b> | "
            f"Sắc thái: {sentiment_emoji} {sentiment_display}\n"
            f"📁 Phân loại: {categories}\n"
            f"🎯 Phạm vi: {scope}\n"
        )

        if entities:
            message += f"👥 Đối tượng: {entities}\n"

        message += rumor_flag

        if processed_data.citations:
            message += "\n\n🔗 <b>Nguồn tin liên quan:</b>"
            for cite in processed_data.citations:
                if isinstance(cite, dict):
                    cite_domain = cite.get("domain", "Nguồn")
                    cite_url = cite.get("source_url", "")
                    cite_title = cite.get("title", "")
                else:
                    cite_domain = getattr(cite, "domain", "Nguồn") or "Nguồn"
                    cite_url = getattr(cite, "source_url", "") or ""
                    cite_title = getattr(cite, "title", "") or ""
                
                if cite_url:
                    message += f"\n• <a href='{cite_url}'>{cite_domain}</a>: {cite_title}"
        elif processed_data.source_url:
            message += f"\n\n🔗 <a href='{processed_data.source_url}'>Xem bài viết gốc</a>"

        message += f"\n\n🤖 Rule: {rule.rule_name}"

        return message
