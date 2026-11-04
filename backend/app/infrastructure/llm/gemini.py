"""
GeminiImplementation — Concrete LLM service using Google Gemini.
Implements ILLMService interface (PRD Section 9.1).
Supports key rotation, Free Tier rate limiting (RPM/TPM/RPD via KeyPool),
exponential backoff on 503/429, structured JSON output, and DB configuration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
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


class GeminiImplementation(ILLMService):
    """
    Google Gemini implementation of ILLMService.

    Design:
      - Config (API keys, model name, prompts) is fetched from DB once per
        crawl cycle via _ensure_config() and held in instance-level cache.
      - Uses process-wide KeyPool (`get_pool()`) to enforce Free Tier RPM/TPM/RPD
        limits across all requests and rotate keys based on earliest availability.
      - Always uses `gemini-3.8-flash` with `thinking_level=HIGH` and structured
        JSON schema output.
      - Handles 429 (cooldown key and switch to next key) and 503 (exponential
        backoff with jitter across keys).
    """

    def __init__(self) -> None:
        self.llm_config_repo = LLMConfigRepository()
        self.llm_prompt_repo = LLMPromptRepository()
        self._cached_keys: list[str] | None = None
        self._cached_model: str | None = None
        self._cached_sys_prompt: str | None = None
        self._cached_batch_prompt: str | None = None
        self._clients: dict[str, genai.Client] = {}

    def _get_client(self, key: str) -> genai.Client:
        client = self._clients.get(key)
        if client is None:
            client = genai.Client(api_key=key)
            self._clients[key] = client
        return client

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
            self._cached_model = DEFAULT_MODEL
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
        else:
            if isinstance(prompt_result, Exception):
                logger.error(f"Error fetching LLM prompts from DB: {prompt_result}")
            self._cached_sys_prompt = SYSTEM_PROMPT
            self._cached_batch_prompt = BATCH_SYSTEM_PROMPT

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
        Uses KeyPool for Free Tier RPM/TPM/RPD enforcement and key rotation.
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
        model_to_try = DEFAULT_MODEL
        last_error: Exception | None = None
        max_attempts = max(4, len(keys) * 3)

        for attempt in range(max_attempts):
            key = await pool.acquire(keys, est_tokens)
            client = self._get_client(key)
            try:
                response = await client.aio.models.generate_content(
                    model=model_to_try,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self._cached_batch_prompt,
                        temperature=0.1,
                        max_output_tokens=65536,
                        thinking_config=self._thinking_config(),
                        response_mime_type="application/json",
                        response_json_schema=BATCH_RESPONSE_SCHEMA,
                    ),
                )

                actual_tok = getattr(getattr(response, "usage_metadata", None), "total_token_count", None)
                pool.report_success(key, actual_tok, est_tokens)
                self._cached_model = model_to_try

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
                    f"Batch JSON parse error (attempt {attempt + 1}/{max_attempts}, key {mask_key(key)}): {e}"
                )
                await asyncio.sleep(2.0)
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                if code == 429:
                    retry_after, daily = parse_retry_delay(getattr(e, "details", None))
                    pool.report_rate_limited(key, retry_after, daily)
                    continue
                if code in (401, 403):
                    pool.disable(key, 1800.0)
                    continue
                if code in (500, 502, 503, 504):
                    backoff = min(45.0, (2 ** min(attempt, 4)) * 3.0 + random.uniform(1.0, 4.0))
                    logger.warning(
                        f"Gemini {code} overloaded (attempt {attempt + 1}/{max_attempts}, "
                        f"key {mask_key(key)}) — backing off {backoff:.1f}s..."
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error(f"Batch API error (key {mask_key(key)}): {e}")
                break
            except QuotaExhausted:
                raise
            except Exception as e:
                last_error = e
                logger.error(f"Batch unexpected error (key {mask_key(key)}): {e}")
                await asyncio.sleep(3.0)

        logger.error(f"Gemini batch analysis failed after {max_attempts} attempts: {last_error}")
        raise RuntimeError(f"Gemini batch analysis failed: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _thinking_config() -> types.ThinkingConfig:
        """Always use HIGH thinking effort for best accuracy on gemini-3.8-flash."""
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)

    async def _call_single_with_pool(
        self, keys: list[str], raw_text: str, title: str = ""
    ) -> dict:
        user_prompt = f"Tiêu đề: {title}\n\nNội dung:\n{(raw_text or '')[:4000]}"
        est_tokens = estimate_tokens((self._cached_sys_prompt or "") + user_prompt) + 1024
        pool = get_pool()
        model_to_try = DEFAULT_MODEL
        last_error: Exception | None = None
        max_attempts = max(4, len(keys) * 2)

        for attempt in range(max_attempts):
            key = await pool.acquire(keys, est_tokens)
            client = self._get_client(key)
            try:
                response = await client.aio.models.generate_content(
                    model=model_to_try,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self._cached_sys_prompt,
                        temperature=0.1,
                        max_output_tokens=8192,
                        thinking_config=self._thinking_config(),
                        response_mime_type="application/json",
                        response_json_schema=SINGLE_RESPONSE_SCHEMA,
                    ),
                )
                actual_tok = getattr(getattr(response, "usage_metadata", None), "total_token_count", None)
                pool.report_success(key, actual_tok, est_tokens)
                self._cached_model = model_to_try
                parsed = self._parse_llm_json(response.text or "{}")
                if not isinstance(parsed, dict):
                    raise ValueError("LLM did not return a JSON object")
                return self._validate_response(parsed)

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"Single JSON parse error (attempt {attempt + 1}/{max_attempts}): {e}")
                await asyncio.sleep(2.0)
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                if code == 429:
                    retry_after, daily = parse_retry_delay(getattr(e, "details", None))
                    pool.report_rate_limited(key, retry_after, daily)
                    continue
                if code in (401, 403):
                    pool.disable(key, 1800.0)
                    continue
                if code in (500, 502, 503, 504):
                    backoff = min(30.0, (2 ** min(attempt, 4)) * 2.5 + random.uniform(0.5, 2.5))
                    logger.warning(
                        f"Single Gemini {code} (attempt {attempt + 1}/{max_attempts}, "
                        f"key {mask_key(key)}) — waiting {backoff:.1f}s..."
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error(f"Gemini single API error: {e}")
                break
            except QuotaExhausted:
                raise
            except Exception as e:
                last_error = e
                logger.error(f"Single unexpected error (attempt {attempt + 1}/{max_attempts}): {e}")
                await asyncio.sleep(2.0)

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
