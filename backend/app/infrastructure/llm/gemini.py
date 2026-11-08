"""
GeminiImplementation — Concrete LLM service using Google Gemini.
Implements ILLMService interface (PRD Section 9.1).
Supports key rotation, multi-model fallback across per-model Free Tier quotas
(RPM/TPM/RPD via KeyPool), structured JSON output, and DB configuration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from google import genai
from google.genai import types, errors

from app.config import settings
from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import LLMConfigRepository, LLMPromptRepository
from app.infrastructure.llm.prompts import (
    SYSTEM_PROMPT,
    BATCH_SYSTEM_PROMPT,
    SINGLE_RESPONSE_SCHEMA,
    BATCH_RESPONSE_SCHEMA,
    validate_llm_item,
)
from app.infrastructure.llm.quota import (
    QuotaExhausted,
    estimate_tokens,
    get_pool,
    mask_key,
    parse_retry_delay,
)

logger = logging.getLogger(__name__)

# Matches optional language tag after opening fence: ```json\n...\n```
_FENCE_RE = re.compile(r"^```[a-z]*\n?(.*?)\n?```$", re.DOTALL)

DEFAULT_MODEL = "gemini-3.8-flash"

# Ordered fallback chain across distinct Gemini models (each has its own 20 RPD Free Tier quota)
FALLBACK_MODELS: list[str] = [
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]


class GeminiImplementation(ILLMService):
    """
    Google Gemini implementation of ILLMService.

    Design:
      - Config (API keys, model name, prompts) is fetched from DB once per
        crawl cycle via _ensure_config() and held in instance-level cache.
      - Uses process-wide KeyPool (`get_pool()`) to enforce Free Tier RPM/TPM/RPD
        limits per (key, model) slot and rotate across both keys and fallback models.
      - Disables google-genai internal 5x retry (`HttpRetryOptions(attempts=1)`) so a
        single 429/503 does not silently burn 5 RPD requests or hang for 2+ minutes.
    """

    def __init__(self) -> None:
        self.llm_config_repo = LLMConfigRepository()
        self.llm_prompt_repo = LLMPromptRepository()
        self._cached_keys: list[str] | None = None
        self._cached_model: str | None = None
        self._cached_sys_prompt: str | None = None
        self._cached_batch_prompt: str | None = None
        self._cached_prompt_name: str | None = None
        self._clients: dict[str, genai.Client] = {}
        self.start_run_tracking()

    def _get_client(self, key: str) -> genai.Client:
        client = self._clients.get(key)
        if client is None:
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=45000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            self._clients[key] = client
        return client

    def _get_models_to_try(self) -> list[str]:
        primary = self._cached_model or DEFAULT_MODEL
        models = [primary] + [m for m in FALLBACK_MODELS if m != primary]
        return models

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    async def _load_config(self) -> None:
        configs_result, prompt_result = await asyncio.gather(
            self.llm_config_repo.find_default_configs(),
            self.llm_prompt_repo.find_active(),
            return_exceptions=True,
        )

        # --- Keys + model ---
        keys: list[str] = []
        if isinstance(configs_result, list) and configs_result:
            keys = [c["api_key"].strip() for c in configs_result if c.get("api_key") and c["api_key"].strip()]
            db_model = (configs_result[0].get("model_name") or "").strip()
            self._cached_model = db_model if db_model else DEFAULT_MODEL
        else:
            if isinstance(configs_result, Exception):
                logger.error(f"Error fetching LLM configs from DB: {configs_result}")
            self._cached_model = DEFAULT_MODEL

        # Fallback/supplement with env key if not already included
        fallback_key = (settings.gemini_api_key or "").strip()
        if fallback_key and fallback_key not in keys:
            keys.append(fallback_key)

        self._cached_keys = list(dict.fromkeys(keys))

        # --- Prompts ---
        if isinstance(prompt_result, dict) and prompt_result:
            sys_p = prompt_result.get("system_prompt")
            batch_p = prompt_result.get("batch_system_prompt")
            self._cached_sys_prompt = sys_p if sys_p else SYSTEM_PROMPT
            self._cached_batch_prompt = batch_p if batch_p else BATCH_SYSTEM_PROMPT
            self._cached_prompt_name = prompt_result.get("name") or "Prompt LTIA Radar v2.0"
        else:
            if isinstance(prompt_result, Exception):
                logger.error(f"Error fetching LLM prompts from DB: {prompt_result}")
            self._cached_sys_prompt = SYSTEM_PROMPT
            self._cached_batch_prompt = BATCH_SYSTEM_PROMPT
            self._cached_prompt_name = "Mặc định hệ thống"

    async def _ensure_config(self) -> None:
        if self._cached_keys is None:
            await self._load_config()

    def invalidate_cache(self) -> None:
        self._cached_keys = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_rate_limit(self) -> int:
        """Get effective RPM across all active keys."""
        await self._ensure_config()
        num_keys = max(1, len(self._cached_keys or []))
        return settings.llm_rpm_per_key * num_keys

    def start_run_tracking(self) -> None:
        """Start/reset metrics tracking for an operational crawl cycle."""
        self._run_calls_count = 0
        self._run_tokens_used = 0
        self._run_models_used: list[str] = []
        self._run_keys_used: list[str] = []
        self._run_errors_429 = 0
        self._run_errors_503 = 0
        self._run_errors_other = 0
        self._run_errors: list[str] = []

    async def get_run_metrics(self) -> dict:
        """Retrieve LLM metrics and execution details for the current/latest cycle."""
        await self._ensure_config()
        active_keys = self._cached_keys or []
        active_key_suffixes = [f"...{k[-4:]}" for k in active_keys if len(k) >= 4]
        used_key_suffixes = [f"...{k[-4:]}" for k in getattr(self, "_run_keys_used", []) if len(k) >= 4]
        models_used = getattr(self, "_run_models_used", [])
        calls = getattr(self, "_run_calls_count", 0)
        tokens = getattr(self, "_run_tokens_used", 0)
        errors = getattr(self, "_run_errors", [])
        prompt_name = getattr(self, "_cached_prompt_name", "") or "Prompt LTIA Radar v2.0"

        model_name = models_used[0] if models_used else (self._cached_model or DEFAULT_MODEL)

        pool = get_pool()
        status = "success" if calls > 0 else "idle"
        if errors and calls == 0:
            status = "failed"
        elif errors and calls > 0:
            status = "partial_error"

        return {
            "provider": "Google Gemini",
            "model_name": model_name,
            "all_models_used": list(dict.fromkeys(models_used)),
            "key_suffixes": list(dict.fromkeys(used_key_suffixes or active_key_suffixes)),
            "calls_count": calls,
            "tokens_used": tokens,
            "free_tpm_limit": pool.tpm,
            "free_rpd_limit": pool.rpd,
            "free_rpm_limit": pool.rpm,
            "errors_429": getattr(self, "_run_errors_429", 0),
            "errors_503": getattr(self, "_run_errors_503", 0),
            "errors_other": getattr(self, "_run_errors_other", 0),
            "prompt_name": prompt_name,
            "status": status,
            "errors": errors,
        }

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        """Extract insights for a single article using Free Tier key pool & rotation."""
        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Gemini API key configured, returning default analysis")
            return self._default_response(title)

        return await self._call_single_with_pool(keys, raw_text, title)

    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        """
        Extract clustered insights for a batch of articles in a single prompt.
        Uses KeyPool for Free Tier RPM/TPM/RPD enforcement and key + model rotation.
        """
        if not articles:
            return []

        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Gemini API key configured, returning default analyses")
            return [
                {**self._default_response(a.get("title", "")), "source_indices": [idx]}
                for idx, a in enumerate(articles)
            ]

        input_data = [
            {
                "index": idx,
                "title": a.get("title", ""),
                "content": (a.get("raw_text") or "")[:3500],
                "source": a.get("domain", ""),
                "published": a.get("publish_time", ""),
            }
            for idx, a in enumerate(articles)
        ]
        user_prompt = json.dumps(input_data, ensure_ascii=False)
        est_tokens = estimate_tokens((self._cached_batch_prompt or "") + user_prompt) + 2048

        pool = get_pool()
        models_to_try = self._get_models_to_try()
        last_error: Exception | None = None
        max_attempts = max(6, len(keys) * len(models_to_try))

        for attempt in range(max_attempts):
            key, model_to_try = await pool.acquire_slot(keys, models_to_try, est_tokens)
            client = self._get_client(key)
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=self._cached_batch_prompt,
                    temperature=0.1,
                    max_output_tokens=65536,
                    response_mime_type="application/json",
                    response_json_schema=BATCH_RESPONSE_SCHEMA,
                )
                thinking_cfg = self._thinking_config(model_to_try)
                if thinking_cfg is not None:
                    cfg.thinking_config = thinking_cfg

                response = await client.aio.models.generate_content(
                    model=model_to_try,
                    contents=user_prompt,
                    config=cfg,
                )

                actual_tok = getattr(getattr(response, "usage_metadata", None), "total_token_count", None)
                pool.report_success(key, actual_tok, est_tokens, model=model_to_try)
                if not hasattr(self, "_run_calls_count"):
                    self.start_run_tracking()
                self._run_calls_count += 1
                self._run_tokens_used += int(actual_tok or est_tokens or 0)
                if model_to_try not in self._run_models_used:
                    self._run_models_used.append(model_to_try)
                if key not in self._run_keys_used:
                    self._run_keys_used.append(key)
                logger.info(
                    f"✨ Gemini batch OK (model={model_to_try}, key={mask_key(key)}, "
                    f"tokens={actual_tok or est_tokens})"
                )

                parsed = self._parse_llm_json(response.text or "[]")
                if not isinstance(parsed, list):
                    raise ValueError("LLM did not return a JSON list")

                final_clusters: list[dict] = []
                covered_indices: set[int] = set()

                for cluster in parsed:
                    if not isinstance(cluster, dict):
                        continue
                    indices = cluster.get("source_indices", [])
                    if not indices:
                        idx = cluster.get("index")
                        if idx is not None:
                            indices = [idx]

                    # Filter out-of-range or duplicate indices across clusters
                    valid_indices = [
                        i
                        for i in indices
                        if isinstance(i, int) and 0 <= i < len(articles) and i not in covered_indices
                    ]
                    if not valid_indices:
                        continue

                    cluster["source_indices"] = valid_indices
                    covered_indices.update(valid_indices)
                    final_clusters.append(self._validate_response(cluster))

                # Handle any indices omitted by the LLM
                missing_indices = [i for i in range(len(articles)) if i not in covered_indices]
                for idx in missing_indices:
                    a = articles[idx]
                    logger.warning(
                        f"Batch index {idx} missing in clustered LLM response — calling singular extract"
                    )
                    try:
                        single = await self._call_single_with_pool(
                            keys, a.get("raw_text", ""), a.get("title", "")
                        )
                        single["source_indices"] = [idx]
                        final_clusters.append(single)
                    except Exception as ex:
                        logger.error(f"Single fallback failed for index {idx}: {ex}")
                        default_resp = self._default_response(a.get("title", ""))
                        default_resp["source_indices"] = [idx]
                        final_clusters.append(default_resp)

                return final_clusters

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(
                    f"Batch JSON parse error (attempt {attempt + 1}/{max_attempts}, "
                    f"model {model_to_try}, key {mask_key(key)}): {e}"
                )
                await asyncio.sleep(1.5)
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                if code == 429:
                    self._run_errors_429 += 1
                    retry_after, daily = parse_retry_delay(getattr(e, "details", None))
                    pool.report_rate_limited(key, retry_after, daily, model=model_to_try)
                    self._run_errors.append(f"429 RateLimit [{model_to_try}] ({mask_key(key)}): retry in {retry_after or 'cooldown'}s")
                    continue
                if code in (401, 403):
                    self._run_errors_other += 1
                    pool.disable(key, 1800.0)
                    self._run_errors.append(f"{code} AuthError [{model_to_try}] ({mask_key(key)})")
                    continue
                if code == 404:
                    self._run_errors_other += 1
                    pool.report_overloaded(key, model=model_to_try, cooldown_s=3600.0)
                    self._run_errors.append(f"404 NotFound [{model_to_try}] ({mask_key(key)})")
                    continue
                if code in (500, 502, 503, 504):
                    self._run_errors_503 += 1
                    pool.report_overloaded(key, model=model_to_try, cooldown_s=90.0)
                    self._run_errors.append(f"{code} Overload [{model_to_try}] ({mask_key(key)})")
                    continue
                self._run_errors_other += 1
                logger.error(f"Batch API error (model {model_to_try}, key {mask_key(key)}): {e}")
                pool.report_overloaded(key, model=model_to_try, cooldown_s=60.0)
                self._run_errors.append(f"APIError [{model_to_try}]: {e}")
                continue
            except QuotaExhausted:
                raise
            except Exception as e:
                last_error = e
                self._run_errors_other += 1
                self._run_errors.append(f"NetworkError [{model_to_try}]: {type(e).__name__}")
                logger.warning(
                    f"Batch timeout/network error (attempt {attempt + 1}/{max_attempts}, "
                    f"model {model_to_try}, key {mask_key(key)}): {type(e).__name__}: {e}"
                )
                pool.report_overloaded(key, model=model_to_try, cooldown_s=90.0)
                continue

        logger.error(f"Gemini batch analysis failed after {max_attempts} attempts: {last_error}")
        raise RuntimeError(f"Gemini batch analysis failed: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _thinking_config(model: str = DEFAULT_MODEL) -> types.ThinkingConfig | None:
        """Use HIGH thinking effort on Gemini 3.x models; omit for 2.5 models."""
        if model.startswith("gemini-3"):
            return types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
        return None

    async def _call_single_with_pool(
        self, keys: list[str], raw_text: str, title: str = ""
    ) -> dict:
        user_prompt = f"Tiêu đề: {title}\n\nNội dung:\n{(raw_text or '')[:4000]}"
        est_tokens = estimate_tokens((self._cached_sys_prompt or "") + user_prompt) + 1024
        pool = get_pool()
        models_to_try = self._get_models_to_try()
        last_error: Exception | None = None
        max_attempts = max(6, len(keys) * len(models_to_try))

        for attempt in range(max_attempts):
            key, model_to_try = await pool.acquire_slot(keys, models_to_try, est_tokens)
            client = self._get_client(key)
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=self._cached_sys_prompt,
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_json_schema=SINGLE_RESPONSE_SCHEMA,
                )
                thinking_cfg = self._thinking_config(model_to_try)
                if thinking_cfg is not None:
                    cfg.thinking_config = thinking_cfg

                response = await client.aio.models.generate_content(
                    model=model_to_try,
                    contents=user_prompt,
                    config=cfg,
                )
                actual_tok = getattr(getattr(response, "usage_metadata", None), "total_token_count", None)
                pool.report_success(key, actual_tok, est_tokens, model=model_to_try)
                if not hasattr(self, "_run_calls_count"):
                    self.start_run_tracking()
                self._run_calls_count += 1
                self._run_tokens_used += int(actual_tok or est_tokens or 0)
                if model_to_try not in self._run_models_used:
                    self._run_models_used.append(model_to_try)
                if key not in self._run_keys_used:
                    self._run_keys_used.append(key)
                parsed = self._parse_llm_json(response.text or "{}")
                if not isinstance(parsed, dict):
                    raise ValueError("LLM did not return a JSON object")
                return self._validate_response(parsed)

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"Single JSON parse error (attempt {attempt + 1}/{max_attempts}): {e}")
                await asyncio.sleep(1.5)
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                if code == 429:
                    self._run_errors_429 += 1
                    retry_after, daily = parse_retry_delay(getattr(e, "details", None))
                    pool.report_rate_limited(key, retry_after, daily, model=model_to_try)
                    self._run_errors.append(f"429 RateLimit [{model_to_try}] ({mask_key(key)}): retry in {retry_after or 'cooldown'}s")
                    continue
                if code in (401, 403):
                    self._run_errors_other += 1
                    pool.disable(key, 1800.0)
                    self._run_errors.append(f"{code} AuthError [{model_to_try}] ({mask_key(key)})")
                    continue
                if code == 404:
                    self._run_errors_other += 1
                    pool.report_overloaded(key, model=model_to_try, cooldown_s=3600.0)
                    self._run_errors.append(f"404 NotFound [{model_to_try}] ({mask_key(key)})")
                    continue
                if code in (500, 502, 503, 504):
                    self._run_errors_503 += 1
                    pool.report_overloaded(key, model=model_to_try, cooldown_s=90.0)
                    self._run_errors.append(f"{code} Overload [{model_to_try}] ({mask_key(key)})")
                    continue
                self._run_errors_other += 1
                logger.error(f"Gemini single API error: {e}")
                pool.report_overloaded(key, model=model_to_try, cooldown_s=60.0)
                self._run_errors.append(f"APIError [{model_to_try}]: {e}")
                continue
            except QuotaExhausted:
                raise
            except Exception as e:
                last_error = e
                self._run_errors_other += 1
                self._run_errors.append(f"NetworkError [{model_to_try}]: {type(e).__name__}")
                logger.warning(
                    f"Single timeout/network error (attempt {attempt + 1}/{max_attempts}, "
                    f"model {model_to_try}): {type(e).__name__}: {e}"
                )
                pool.report_overloaded(key, model=model_to_try, cooldown_s=90.0)
                continue

        raise RuntimeError(f"Gemini single analysis failed: {last_error}")

    @staticmethod
    def _parse_llm_json(text: str) -> dict | list:
        stripped = text.strip()
        match = _FENCE_RE.match(stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    @staticmethod
    def _validate_response(data: dict) -> dict:
        return validate_llm_item(data)

    @staticmethod
    def _default_response(title: str = "") -> dict:
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
