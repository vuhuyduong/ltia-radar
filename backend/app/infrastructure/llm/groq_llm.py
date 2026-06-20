import asyncio
import json
import logging
import random
import re

import groq
from groq import AsyncGroq

from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import LLMConfigRepository, LLMPromptRepository

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```[a-z]*\n?(.*?)\n?```$", re.DOTALL)

class GroqImplementation(ILLMService):
    def __init__(self) -> None:
        self.llm_config_repo = LLMConfigRepository()
        self.llm_prompt_repo = LLMPromptRepository()
        self._cached_keys: list[str] | None = None
        self._cached_model: str | None = None
        self._cached_sys_prompt: str | None = None
        self._cached_batch_prompt: str | None = None

    async def _ensure_config(self) -> None:
        if self._cached_keys is not None:
            return

        cursor = self.llm_config_repo.collection.find({"is_active": True, "provider": "groq"})
        configs = [doc async for doc in cursor]
        if configs:
            self._cached_keys = [c["api_key"] for c in configs if c.get("api_key")]
            self._cached_model = configs[0]["model_name"]
        else:
            self._cached_keys = []
            self._cached_model = "llama-3.3-70b-versatile"

        from app.infrastructure.llm.gemini import SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT
        prompt_doc = await self.llm_prompt_repo.find_active()
        if prompt_doc:
            self._cached_sys_prompt = prompt_doc.get("system_prompt", SYSTEM_PROMPT)
            self._cached_batch_prompt = prompt_doc.get("batch_system_prompt", BATCH_SYSTEM_PROMPT)
        else:
            self._cached_sys_prompt = SYSTEM_PROMPT
            self._cached_batch_prompt = BATCH_SYSTEM_PROMPT

    def invalidate_cache(self) -> None:
        self._cached_keys = None
        self._cached_model = None
        self._cached_sys_prompt = None
        self._cached_batch_prompt = None

    def _get_fallback_models(self) -> list[str]:
        base_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        current = self._cached_model or "llama-3.3-70b-versatile"
        if current in base_models:
            return base_models[base_models.index(current):]
        return [current] + base_models

    async def extract_insight(self, raw_text: str, title: str = "") -> dict:
        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Groq API key configured")
            return self._default_response(title)

        client = AsyncGroq(api_key=random.choice(keys))
        return await self._call_single(client, raw_text, title)

    async def extract_insights_batch(self, articles: list[dict]) -> list[dict]:
        if not articles:
            return []

        await self._ensure_config()
        keys = self._cached_keys or []
        if not keys:
            logger.warning("No Groq API key configured")
            return [self._default_response(a.get("title", "")) for a in articles]

        input_data = [
            {
                "index": idx,
                "title": a.get("title", ""),
                "content": a.get("raw_text", "")[:4000],
            }
            for idx, a in enumerate(articles)
        ]
        user_prompt = json.dumps(input_data, ensure_ascii=False)

        shuffled_keys = keys[:]
        random.shuffle(shuffled_keys)
        clients = [(AsyncGroq(api_key=k), k) for k in shuffled_keys]

        last_error: Exception | None = None

        for client, key in clients:
            final_clusters: list[dict] | None = None
            for model_to_try in self._get_fallback_models():
                for attempt in range(3):
                    try:
                        response = await client.chat.completions.create(
                            model=model_to_try,
                            messages=[
                                {"role": "system", "content": self._cached_batch_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=8192
                        )
                        self._cached_model = model_to_try
                        
                        text = response.choices[0].message.content
                        parsed = self._parse_llm_json(text)
                        
                        # Groq might wrap in {"clusters": [...]} if it feels like it
                        if isinstance(parsed, dict) and "clusters" in parsed:
                            parsed = parsed["clusters"]
                        elif isinstance(parsed, dict) and "data" in parsed:
                            parsed = parsed["data"]
                            
                        if not isinstance(parsed, list):
                            raise ValueError("LLM did not return a list")

                        final_clusters = []
                        covered_indices = set()

                        for cluster in parsed:
                            indices = cluster.get("source_indices", [])
                            if not indices:
                                idx = cluster.get("index")
                                if idx is not None:
                                    indices = [idx]

                            valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < len(articles)]
                            if not valid_indices:
                                continue

                            cluster["source_indices"] = valid_indices
                            covered_indices.update(valid_indices)
                            final_clusters.append(self._validate_response(cluster))

                        missing_indices = [i for i in range(len(articles)) if i not in covered_indices]
                        for idx in missing_indices:
                            a = articles[idx]
                            logger.warning(f"Batch index {idx} missing in clustered Groq response")
                            try:
                                single = await self._call_single(client, a.get("raw_text", ""), a.get("title", ""))
                                single["source_indices"] = [idx]
                                final_clusters.append(single)
                            except Exception as ex:
                                default_resp = self._default_response(a.get("title", ""))
                                default_resp["source_indices"] = [idx]
                                final_clusters.append(default_resp)

                        return final_clusters

                    except json.JSONDecodeError as e:
                        last_error = e
                        logger.warning(f"Batch JSON parse error: {e}")
                    except groq.APIStatusError as e:
                        last_error = e
                        if e.status_code == 404:
                            logger.warning(f"Model {model_to_try} not found (404), falling back.")
                            break
                        elif e.status_code == 429:
                            logger.warning(f"Rate limit (429) on {model_to_try}.")
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"Batch API error: {e}")
                            break
                    except Exception as e:
                        last_error = e
                        logger.error(f"Batch unexpected error: {e}")
                        break

        raise RuntimeError(f"Groq batch analysis failed: {last_error}")

    async def _call_single(self, client: AsyncGroq, raw_text: str, title: str = "") -> dict:
        user_prompt = f"Tiêu đề: {title}\n\nNội dung:\n{raw_text[:4000]}"
        last_error: Exception | None = None

        for model_to_try in self._get_fallback_models():
            for attempt in range(3):
                try:
                    response = await client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {"role": "system", "content": self._cached_sys_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1024,
                        response_format={"type": "json_object"}
                    )
                    self._cached_model = model_to_try
                    
                    text = response.choices[0].message.content
                    return self._validate_response(self._parse_llm_json(text))

                except json.JSONDecodeError as e:
                    last_error = e
                    logger.warning(f"JSON parse error: {e}")
                except groq.APIStatusError as e:
                    last_error = e
                    if e.status_code == 404:
                        logger.warning(f"Model {model_to_try} not found (404), falling back.")
                        break
                    elif e.status_code == 429:
                        await asyncio.sleep(2)
                    else:
                        break
                except Exception as e:
                    last_error = e
                    break

        raise RuntimeError(f"Groq single analysis failed: {last_error}")

    @staticmethod
    def _parse_llm_json(text: str) -> dict | list:
        stripped = text.strip()
        match = _FENCE_RE.match(stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    @staticmethod
    def _validate_response(data: dict) -> dict:
        valid_sentiments = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
        valid_impacts = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        return {
            "source_indices": data.get("source_indices", []),
            "category": data.get("category", []),
            "sentiment": data.get("sentiment", "NEUTRAL") if data.get("sentiment") in valid_sentiments else "NEUTRAL",
            "target_scope": data.get("target_scope", []),
            "impact_level": data.get("impact_level", "LOW") if data.get("impact_level") in valid_impacts else "LOW",
            "key_entities": data.get("key_entities", []),
            "executive_summary": data.get("executive_summary", ""),
            "is_rumor": bool(data.get("is_rumor", False)),
            "is_relevant": bool(data.get("is_relevant", True)),
        }

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
