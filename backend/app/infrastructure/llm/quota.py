"""
Điều tiết hạn mức (quota) cho Gemini API — phù hợp Google AI Studio FREE TIER.

Free tier giới hạn theo 3 chiều, vượt BẤT KỲ chiều nào đều trả 429:
  - RPM: số request / phút
  - TPM: số token đầu vào / phút
  - RPD: số request / ngày (reset lúc 00:00 giờ Thái Bình Dương - Pacific Time)

Module này giữ trạng thái theo từng API key trong bộ nhớ (singleton toàn tiến trình, vì
use case/LLM service được tạo mới ở mỗi request nên KHÔNG thể giữ trạng thái trong instance):
  - acquire(): chọn key sẵn sàng sớm nhất, chờ nếu cần, đặt chỗ (reserve) trước khi gọi.
  - report_rate_limited(): khi nhận 429 → cooldown theo retryDelay Google trả về, hoặc đến
    nửa đêm Pacific nếu hết quota ngày.
  - Hết quota toàn bộ key hoặc phải chờ quá lâu → raise QuotaExhausted; chu kỳ crawl dừng
    gọi LLM, các bài chưa xử lý được giữ trạng thái "pending" và thử lại ở chu kỳ sau.

Lưu ý: Google tính quota theo GOOGLE CLOUD PROJECT, không theo API key. Nếu hai key thuộc
cùng một project, hạn mức bị dùng chung — hãy tạo key ở các project khác nhau để thực sự
nhân đôi hạn mức.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_PT = ZoneInfo("America/Los_Angeles")


class QuotaExhausted(RuntimeError):
    """Mọi API key đều hết/đang bị giới hạn quota trong khoảng chờ cho phép."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def mask_key(key: str) -> str:
    return f"{key[:6]}…{key[-4:]}" if len(key) > 12 else "***"


def seconds_until_pacific_midnight(now: datetime | None = None) -> float:
    now = now.astimezone(_PT) if now else datetime.now(_PT)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    return max(1.0, (tomorrow - now).total_seconds())


def estimate_tokens(text: str) -> int:
    """Ước lượng thô số token tiếng Việt (~2.2 ký tự/token, thiên về dư để an toàn)."""
    return math.ceil(len(text) / 2.2)


def parse_retry_delay(details: object) -> tuple[float | None, bool]:
    """
    Trích (retry_after_giây, là_quota_ngày) từ phần details của lỗi 429 Google.

    Google trả google.rpc.RetryInfo.retryDelay (vd "34s") và QuotaFailure.violations[].quotaId
    (vd "GenerateRequestsPerDayPerProjectPerModel-FreeTier").
    """
    retry_after: float | None = None
    daily = False
    err = details.get("error", details) if isinstance(details, dict) else {}
    items = err.get("details", []) if isinstance(err, dict) else []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        t = str(item.get("@type", ""))
        if t.endswith("RetryInfo"):
            m = re.match(r"^([\d.]+)s$", str(item.get("retryDelay", "")))
            if m:
                retry_after = float(m.group(1))
        if t.endswith("QuotaFailure"):
            for v in item.get("violations", []) or []:
                qid = str(v.get("quotaId", "")) + str(v.get("quotaMetric", ""))
                if "PerDay" in qid or "per_day" in qid.lower():
                    daily = True
    return retry_after, daily


@dataclass
class _KeyState:
    req_times: deque = field(default_factory=deque)  # monotonic timestamps trong 60s gần nhất
    tok_times: deque = field(default_factory=deque)  # (monotonic, tokens) trong 60s gần nhất
    day: str = ""  # ngày Pacific hiện tại
    day_count: int = 0
    cooldown_until: float = 0.0  # monotonic


class KeyPool:
    """Bộ điều tiết RPM/TPM/RPD theo từng key + cooldown khi bị 429."""

    def __init__(
        self,
        rpm: int,
        tpm: int,
        rpd: int,
        max_wait_seconds: float = 180.0,
    ) -> None:
        self.rpm = max(1, rpm)
        self.tpm = max(1000, tpm)
        self.rpd = max(1, rpd)
        self.max_wait = max_wait_seconds
        self._states: dict[str, _KeyState] = {}
        self._lock = asyncio.Lock()

    def configure(self, rpm: int, tpm: int, rpd: int, max_wait_seconds: float) -> None:
        self.rpm, self.tpm, self.rpd = max(1, rpm), max(1000, tpm), max(1, rpd)
        self.max_wait = max_wait_seconds

    # -- nội bộ -----------------------------------------------------------

    def _state(self, key: str) -> _KeyState:
        st = self._states.get(key)
        if st is None:
            st = self._states[key] = _KeyState()
        return st

    @staticmethod
    def _prune(st: _KeyState, now: float) -> None:
        while st.req_times and now - st.req_times[0] >= 60.0:
            st.req_times.popleft()
        while st.tok_times and now - st.tok_times[0][0] >= 60.0:
            st.tok_times.popleft()
        today = datetime.now(_PT).strftime("%Y-%m-%d")
        if st.day != today:
            st.day, st.day_count = today, 0

    def _wait_needed(self, st: _KeyState, est_tokens: int, now: float) -> float:
        """Số giây cần chờ để key này gọi được; math.inf nếu hết quota ngày."""
        self._prune(st, now)
        if st.day_count >= self.rpd:
            return max(st.cooldown_until - now, seconds_until_pacific_midnight())
        wait = max(0.0, st.cooldown_until - now)
        if len(st.req_times) >= self.rpm:
            wait = max(wait, st.req_times[0] + 60.0 - now)
        used = sum(t for _, t in st.tok_times)
        if used + est_tokens > self.tpm and st.tok_times:
            need = used + est_tokens - self.tpm
            freed = 0
            for ts, tk in st.tok_times:
                freed += tk
                if freed >= need:
                    wait = max(wait, ts + 60.0 - now)
                    break
            else:
                wait = max(wait, st.tok_times[-1][0] + 60.0 - now)
        return wait

    # -- API --------------------------------------------------------------

    async def acquire(
        self, keys: list[str], est_tokens: int, exclude: set[str] | None = None
    ) -> str:
        """Chọn key dùng được sớm nhất, chờ nếu cần, đặt chỗ rồi trả về key."""
        candidates = [k for k in dict.fromkeys(keys) if not exclude or k not in exclude]
        if not candidates:
            raise QuotaExhausted("Không còn API key khả dụng")
        est_tokens = min(est_tokens, self.tpm)  # một request không thể vượt TPM

        while True:
            async with self._lock:
                now = time.monotonic()
                waits = {k: self._wait_needed(self._state(k), est_tokens, now) for k in candidates}
                best = min(waits, key=waits.get)
                wait = waits[best]
                if wait <= 0:
                    st = self._state(best)
                    st.req_times.append(now)
                    st.tok_times.append((now, est_tokens))
                    st.day_count += 1
                    return best
            if wait > self.max_wait:
                raise QuotaExhausted(
                    f"Hết quota hoặc phải chờ {wait:.0f}s (> {self.max_wait:.0f}s) cho mọi key",
                    retry_after=wait,
                )
            logger.info(
                f"⏳ Rate limit Gemini: chờ {wait:.1f}s (key {mask_key(best)}, "
                f"rpm={self.rpm}, tpm={self.tpm}, rpd={self.rpd})"
            )
            await asyncio.sleep(min(wait, 30.0) + 0.05)

    def report_success(self, key: str, actual_tokens: int | None, est_tokens: int) -> None:
        """Hiệu chỉnh số token đã đặt chỗ bằng số liệu thực tế từ usage_metadata."""
        if not actual_tokens:
            return
        st = self._state(key)
        for i in range(len(st.tok_times) - 1, -1, -1):
            ts, tk = st.tok_times[i]
            if tk == min(est_tokens, self.tpm):
                st.tok_times[i] = (ts, actual_tokens)
                break

    def report_rate_limited(
        self, key: str, retry_after: float | None, daily: bool
    ) -> float:
        """Ghi nhận 429: cooldown theo retryDelay (hoặc tới nửa đêm Pacific nếu hết quota ngày)."""
        st = self._state(key)
        if daily:
            delay = seconds_until_pacific_midnight()
            st.day_count = max(st.day_count, self.rpd)
            logger.warning(f"🚫 Key {mask_key(key)} hết quota NGÀY — nghỉ {delay / 3600:.1f}h")
        else:
            delay = (retry_after or 30.0) + 2.0
            logger.warning(f"🚫 Key {mask_key(key)} bị 429 — nghỉ {delay:.0f}s")
        st.cooldown_until = max(st.cooldown_until, time.monotonic() + delay)
        return delay

    def disable(self, key: str, seconds: float) -> None:
        """Tạm khóa key bị từ chối (401/403: key sai/bị thu hồi)."""
        self._state(key).cooldown_until = time.monotonic() + seconds
        logger.error(f"⛔ Key {mask_key(key)} bị từ chối (401/403) — tạm khóa {seconds / 60:.0f} phút")

    def snapshot(self) -> dict:
        """Trạng thái hiện tại (không chứa key đầy đủ) phục vụ chẩn đoán."""
        now = time.monotonic()
        out = {}
        for k, st in self._states.items():
            self._prune(st, now)
            out[mask_key(k)] = {
                "rpm_used": len(st.req_times),
                "tpm_used": sum(t for _, t in st.tok_times),
                "rpd_used": st.day_count,
                "cooldown_s": max(0, round(st.cooldown_until - now)),
            }
        return out


_POOL: KeyPool | None = None


def get_pool() -> KeyPool:
    """Singleton toàn tiến trình, cấu hình từ settings."""
    global _POOL
    from app.config import settings

    if _POOL is None:
        _POOL = KeyPool(
            settings.llm_rpm_per_key,
            settings.llm_tpm_per_key,
            settings.llm_rpd_per_key,
            settings.llm_max_wait_seconds,
        )
    return _POOL
