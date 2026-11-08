"""
Điều tiết hạn mức (quota) cho Gemini API — phù hợp Google AI Studio FREE TIER.

Free tier giới hạn theo 3 chiều trên từng cặp (Google Cloud Project, Model)
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), vượt BẤT KỲ chiều nào đều trả 429:
  - RPM: số request / phút / model
  - TPM: số token đầu vào / phút / model
  - RPD: số request / ngày / model (thường 20 RPD/model trên Free Tier, reset lúc 00:00 Pacific Time)

Module này giữ trạng thái theo từng cặp (API key, model) trong bộ nhớ (singleton toàn tiến trình, vì
use case/LLM service được tạo mới ở mỗi request nên KHÔNG thể giữ trạng thái trong instance):
  - acquire_slot(): duyệt danh sách model theo thứ tự ưu tiên + danh sách key, chọn cặp (key, model)
    sẵn sàng sớm nhất, chờ nếu cần, đặt chỗ (reserve) trước khi gọi.
  - report_rate_limited(): khi nhận 429 → cooldown cặp (key, model) theo retryDelay Google trả về,
    hoặc đến nửa đêm Pacific nếu hết quota ngày của model đó (các model dự phòng khác trên cùng key
    vẫn dùng được bình thường).
  - report_overloaded(): khi nhận 503/timeout → tạm cooldown model đang quá tải để chuyển ngay sang
    model dự phòng kế tiếp mà không đốt RPD vô ích.
  - Hết quota toàn bộ (key, model) hoặc phải chờ quá lâu → raise QuotaExhausted; chu kỳ crawl dừng
    gọi LLM, các bài chưa xử lý được giữ trạng thái "pending" và thử lại ở chu kỳ sau.

Lưu ý: Google tính quota theo GOOGLE CLOUD PROJECT + MODEL. Nếu hai key thuộc
cùng một project, hạn mức từng model bị dùng chung — hãy tạo key ở các project khác nhau để thực sự
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
_DEFAULT_MODEL = "gemini-3.8-flash"


class QuotaExhausted(RuntimeError):
    """Mọi cặp (API key, model) đều hết/đang bị giới hạn quota trong khoảng chờ cho phép."""

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
    errors_429: int = 0
    errors_503: int = 0
    errors_other: int = 0
    total_tokens_today: int = 0
    total_success: int = 0


class KeyPool:
    """Bộ điều tiết RPM/TPM/RPD theo từng cặp (key, model) + cooldown khi bị 429/503."""

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
        self._states: dict[tuple[str, str], _KeyState] = {}
        self._disabled_keys: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def configure(self, rpm: int, tpm: int, rpd: int, max_wait_seconds: float) -> None:
        self.rpm, self.tpm, self.rpd = max(1, rpm), max(1000, tpm), max(1, rpd)
        self.max_wait = max_wait_seconds

    # -- nội bộ -----------------------------------------------------------

    def _state(self, key: str, model: str = _DEFAULT_MODEL) -> _KeyState:
        slot = (key, model)
        st = self._states.get(slot)
        if st is None:
            st = self._states[slot] = _KeyState()
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
            st.errors_429 = 0
            st.errors_503 = 0
            st.errors_other = 0
            st.total_tokens_today = 0
            st.total_success = 0

    def _wait_needed(self, key: str, model: str, est_tokens: int, now: float) -> float:
        """Số giây cần chờ để cặp (key, model) này gọi được."""
        st = self._state(key, model)
        self._prune(st, now)
        key_disabled_until = self._disabled_keys.get(key, 0.0)
        if st.day_count >= self.rpd:
            return max(st.cooldown_until - now, key_disabled_until - now, seconds_until_pacific_midnight())
        wait = max(0.0, st.cooldown_until - now, key_disabled_until - now)
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

    async def acquire_slot(
        self,
        keys: list[str],
        models: list[str],
        est_tokens: int,
        exclude: set[tuple[str, str]] | None = None,
    ) -> tuple[str, str]:
        """
        Chọn cặp (key, model) khả dụng theo thứ tự ưu tiên của `models`.
        Nếu có bất kỳ key nào trên model ưu tiên cao hơn sẵn sàng ngay (wait <= 0),
        ưu tiên chọn ngay cặp đó (key có day_count thấp nhất).
        Nếu mọi cặp đều phải chờ, chọn cặp có thời gian chờ ngắn nhất.
        """
        clean_keys = list(dict.fromkeys(k for k in keys if k))
        clean_models = list(dict.fromkeys(m for m in models if m)) or [_DEFAULT_MODEL]
        candidates = [
            (k, m)
            for m in clean_models
            for k in clean_keys
            if not exclude or (k, m) not in exclude
        ]
        if not candidates:
            raise QuotaExhausted("Không còn cặp (API key, model) khả dụng")

        est_tokens = min(est_tokens, self.tpm)

        while True:
            async with self._lock:
                now = time.monotonic()
                # Bước 1: Duyệt theo thứ tự ưu tiên model, tìm key sẵn sàng ngay (wait <= 0)
                for m in clean_models:
                    ready_keys = [
                        k
                        for k in clean_keys
                        if (not exclude or (k, m) not in exclude)
                        and self._wait_needed(k, m, est_tokens, now) <= 0
                    ]
                    if ready_keys:
                        # Chọn key có số lần gọi trong ngày thấp nhất trên model này để cân bằng tải
                        best_key = min(ready_keys, key=lambda k: self._state(k, m).day_count)
                        st = self._state(best_key, m)
                        st.req_times.append(now)
                        st.tok_times.append((now, est_tokens))
                        st.day_count += 1
                        return best_key, m

                # Bước 2: Chưa cặp nào dùng được ngay -> tìm cặp có wait nhỏ nhất
                waits = {(k, m): self._wait_needed(k, m, est_tokens, now) for k, m in candidates}
                best_slot = min(waits, key=waits.get)
                wait = waits[best_slot]
                if wait <= 0:
                    best_key, best_model = best_slot
                    st = self._state(best_key, best_model)
                    st.req_times.append(now)
                    st.tok_times.append((now, est_tokens))
                    st.day_count += 1
                    return best_key, best_model

            if wait > self.max_wait:
                raise QuotaExhausted(
                    f"Hết quota hoặc phải chờ {wait:.0f}s (> {self.max_wait:.0f}s) cho mọi key & model",
                    retry_after=wait,
                )
            best_key, best_model = best_slot
            logger.info(
                f"⏳ Rate limit Gemini: chờ {wait:.1f}s (key {mask_key(best_key)}, model {best_model}, "
                f"rpm={self.rpm}, tpm={self.tpm}, rpd={self.rpd})"
            )
            await asyncio.sleep(min(wait, 30.0) + 0.05)

    async def acquire(
        self, keys: list[str], est_tokens: int, exclude: set[str] | None = None
    ) -> str:
        """Tương thích ngược: chọn key cho model mặc định."""
        excl_slots = {(k, _DEFAULT_MODEL) for k in exclude} if exclude else None
        key, _ = await self.acquire_slot(keys, [_DEFAULT_MODEL], est_tokens, exclude=excl_slots)
        return key

    def report_success(
        self,
        key: str,
        actual_tokens: int | None,
        est_tokens: int,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        """Hiệu chỉnh số token đã đặt chỗ bằng số liệu thực tế từ usage_metadata."""
        st = self._state(key, model)
        st.total_success += 1
        tok = actual_tokens or est_tokens or 0
        st.total_tokens_today += tok
        if not actual_tokens:
            return
        for i in range(len(st.tok_times) - 1, -1, -1):
            ts, tk = st.tok_times[i]
            if tk == min(est_tokens, self.tpm):
                st.tok_times[i] = (ts, actual_tokens)
                break

    def report_rate_limited(
        self,
        key: str,
        retry_after: float | None,
        daily: bool,
        model: str = _DEFAULT_MODEL,
    ) -> float:
        """Ghi nhận 429 cho cặp (key, model): cooldown theo retryDelay hoặc tới nửa đêm Pacific."""
        st = self._state(key, model)
        st.errors_429 += 1
        if daily:
            delay = retry_after if (retry_after and retry_after > 300) else seconds_until_pacific_midnight()
            st.day_count = max(st.day_count, self.rpd)
            logger.warning(
                f"🚫 Key {mask_key(key)} [{model}] hết quota NGÀY (20 RPD) — nghỉ {delay / 3600:.1f}h "
                f"(chuyển sang model/key dự phòng)"
            )
        else:
            delay = (retry_after or 30.0) + 2.0
            logger.warning(f"🚫 Key {mask_key(key)} [{model}] bị 429 — nghỉ {delay:.0f}s")
        st.cooldown_until = max(st.cooldown_until, time.monotonic() + delay)
        return delay

    def report_overloaded(
        self,
        key: str,
        model: str = _DEFAULT_MODEL,
        cooldown_s: float = 90.0,
    ) -> None:
        """
        Ghi nhận lỗi 503 (High Demand) hoặc Timeout trên `model`.
        Vì lỗi 503 quá tải xảy ra ở phía máy chủ model của Google (áp dụng cho mọi key),
        tạm cooldown toàn bộ các slot của `model` này trong `cooldown_s` giây để chuyển ngay
        sang model dự phòng kế tiếp mà không đốt RPD vô ích.
        """
        until = time.monotonic() + cooldown_s
        st = self._state(key, model)
        st.errors_503 += 1
        st.cooldown_until = max(st.cooldown_until, until)
        for (k, m), state in list(self._states.items()):
            if m == model:
                state.cooldown_until = max(state.cooldown_until, until)
        logger.warning(
            f"⚠️ Model [{model}] đang quá tải (503/Timeout) — tạm cooldown model {cooldown_s:.0f}s, "
            f"chuyển ngay sang model dự phòng"
        )

    def disable(self, key: str, seconds: float) -> None:
        """Tạm khóa key bị từ chối (401/403: key sai/bị thu hồi) trên mọi model."""
        until = time.monotonic() + seconds
        self._disabled_keys[key] = until
        for (k, _), st in self._states.items():
            if k == key:
                st.errors_other += 1
                st.cooldown_until = max(st.cooldown_until, until)
        logger.error(f"⛔ Key {mask_key(key)} bị từ chối (401/403) — tạm khóa {seconds / 60:.0f} phút")

    def snapshot(self) -> dict:
        """Trạng thái hiện tại (không chứa key đầy đủ) phục vụ chẩn đoán chi tiết cho Admin."""
        now = time.monotonic()
        out: dict[str, dict] = {}
        for (k, m), st in self._states.items():
            self._prune(st, now)
            label = f"{mask_key(k)} [{m}]"
            cd = max(0, round(max(st.cooldown_until, self._disabled_keys.get(k, 0.0)) - now))
            out[label] = {
                "key_suffix": f"...{k[-4:]}" if len(k) >= 4 else "***",
                "masked_key": mask_key(k),
                "model": m,
                "rpm_used": len(st.req_times),
                "rpm_limit": self.rpm,
                "tpm_used": sum(t for _, t in st.tok_times),
                "tpm_limit": self.tpm,
                "rpd_used": st.day_count,
                "rpd_limit": self.rpd,
                "total_tokens_today": st.total_tokens_today,
                "total_success": st.total_success,
                "errors_429": st.errors_429,
                "errors_503": st.errors_503,
                "errors_other": st.errors_other,
                "cooldown_s": cd,
                "status": "cooling_down" if cd > 0 else ("quota_exhausted" if st.day_count >= self.rpd else "ready"),
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
