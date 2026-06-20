"""
MongoDB Repository implementations — CRUD operations for all collections.

Fixes applied (audit 2026-06-20):
  - Flaw 5:  find_similar_article replaced with two-phase text-index pipeline
             (MongoDB $text pre-filter → Python SequenceMatcher on ≤20 candidates).
             Requires text index: db.processed_data.create_index([("title", "text")])
  - Flaw 6:  add_citation rewritten as single atomic update_one — no document fetch.
             Self-healing migration logic removed from hot path.
  - Flaw 12: Inline domain-name mapping removed; imports get_friendly_domain instead.
"""

from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.utils.domain_mapper import get_friendly_domain
from app.infrastructure.database.mongodb import MongoDB


def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document _id (ObjectId) to string."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


class SourceRepository:
    """MongoDB repository for Sources collection."""

    @property
    def collection(self):
        return MongoDB.get_db().sources

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active(self) -> list[dict]:
        cursor = self.collection.find({"is_active": True})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def create(self, data: dict) -> dict:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        update_data = {k: v for k, v in data.items() if v is not None}
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )
        return await self.find_by_id(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self.collection.count_documents({})


class KeywordRepository:
    """MongoDB repository for Keywords collection."""

    @property
    def collection(self):
        return MongoDB.get_db().keywords

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active(self) -> list[dict]:
        cursor = self.collection.find({"is_active": True})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def create(self, data: dict) -> dict:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        update_data = {k: v for k, v in data.items() if v is not None}
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )
        return await self.find_by_id(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self.collection.count_documents({})


class RawDataRepository:
    """MongoDB repository for RawData collection."""

    @property
    def collection(self):
        return MongoDB.get_db().raw_data

    async def find_by_url_hash(self, url_hash: str) -> Optional[dict]:
        doc = await self.collection.find_one({"url_hash": url_hash})
        return _serialize_doc(doc) if doc else None

    async def find_by_source_url(self, source_url: str) -> Optional[dict]:
        doc = await self.collection.find_one({"source_url": source_url})
        return _serialize_doc(doc) if doc else None

    async def exists_by_url_hash(self, url_hash: str) -> bool:
        """Check if article already exists (dedup logic per US-2.2)."""
        count = await self.collection.count_documents({"url_hash": url_hash})
        return count > 0

    async def create(self, data: dict) -> dict:
        data["crawl_time"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def get_latest_crawl_time(self) -> Optional[datetime]:
        """Get the crawl time of the most recently crawled raw article."""
        cursor = self.collection.find({}, {"crawl_time": 1}).sort("crawl_time", -1).limit(1)
        docs = [doc async for doc in cursor]
        if docs and "crawl_time" in docs[0]:
            return docs[0]["crawl_time"]
        return None


class ProcessedDataRepository:
    """MongoDB repository for ProcessedData collection."""

    @property
    def collection(self):
        return MongoDB.get_db().processed_data

    async def create(self, data: dict) -> dict:
        data["processed_time"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def find_by_raw_data_id(self, raw_data_id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"raw_data_id": raw_data_id})
        return _serialize_doc(doc) if doc else None

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 20,
        sentiment: Optional[str] = None,
        impact_level: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        target_scope: Optional[str] = None,
    ) -> list[dict]:
        """Find processed articles with optional filters."""
        query: dict = {"is_relevant": {"$ne": False}}

        if sentiment:
            query["sentiment"] = sentiment
        if impact_level:
            query["impact_level"] = impact_level
        if category:
            query["category"] = {"$in": [category]}
        if target_scope:
            query["target_scope"] = {"$in": [target_scope]}
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"executive_summary": {"$regex": search, "$options": "i"}},
            ]
        if date_from or date_to:
            query["processed_time"] = {}
            if date_from:
                query["processed_time"]["$gte"] = date_from
            if date_to:
                query["processed_time"]["$lte"] = date_to

        cursor = (
            self.collection.find(query)
            .sort([("publish_time", -1), ("processed_time", -1)])
            .skip(skip)
            .limit(limit)
        )
        return [_serialize_doc(doc) async for doc in cursor]

    async def count(self, query: Optional[dict] = None) -> int:
        base_query = {"is_relevant": {"$ne": False}}
        if query:
            base_query.update(query)
        return await self.collection.count_documents(base_query)

    async def get_sentiment_distribution(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        query: Optional[dict] = None,
    ) -> list[dict]:
        """Aggregate sentiment counts for pie chart."""
        match_stage: dict = dict(query) if query is not None else {}
        match_stage.setdefault("is_relevant", {"$ne": False})
        if query is None and (date_from or date_to):
            match_stage["processed_time"] = {}
            if date_from:
                match_stage["processed_time"]["$gte"] = date_from
            if date_to:
                match_stage["processed_time"]["$lte"] = date_to

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.append({"$group": {"_id": "$sentiment", "count": {"$sum": 1}}})

        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append({"sentiment": doc["_id"], "count": doc["count"]})
        return results

    async def get_timeline(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        query: Optional[dict] = None,
    ) -> list[dict]:
        """Aggregate article counts by date for timeline chart."""
        match_stage: dict = dict(query) if query is not None else {}
        match_stage.setdefault("is_relevant", {"$ne": False})
        if query is None and (date_from or date_to):
            match_stage["processed_time"] = {}
            if date_from:
                match_stage["processed_time"]["$gte"] = date_from
            if date_to:
                match_stage["processed_time"]["$lte"] = date_to

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.extend([
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {
                                    "$ifNull": ["$publish_time", "$processed_time"]
                                },
                                "timezone": "Asia/Ho_Chi_Minh",
                            }
                        },
                        "sentiment": "$sentiment",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.date": 1}},
        ])

        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append({
                "date": doc["_id"]["date"],
                "sentiment": doc["_id"]["sentiment"],
                "count": doc["count"],
            })
        return results

    async def get_top_risks(self, limit: int = 10, query: Optional[dict] = None) -> list[dict]:
        """Get top N highest risk articles (CRITICAL first, then HIGH)."""
        match_stage = dict(query) if query is not None else {}
        match_stage.setdefault("is_relevant", {"$ne": False})
        # Define priority order
        pipeline = [
            {
                "$match": match_stage
            },
            {
                "$addFields": {
                    "impact_order": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": ["$impact_level", "CRITICAL"]}, "then": 0},
                                {"case": {"$eq": ["$impact_level", "HIGH"]}, "then": 1},
                                {"case": {"$eq": ["$impact_level", "MEDIUM"]}, "then": 2},
                            ],
                            "default": 3,
                        }
                    }
                }
            },
            {"$sort": {"impact_order": 1, "processed_time": -1, "_id": -1}},
            {"$limit": limit},
            {"$project": {"impact_order": 0}},
        ]
        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append(_serialize_doc(doc))
        return results

    async def get_category_distribution(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        query: Optional[dict] = None,
    ) -> list[dict]:
        """Aggregate category counts for bar chart."""
        match_stage: dict = dict(query) if query is not None else {}
        match_stage.setdefault("is_relevant", {"$ne": False})
        if query is None and (date_from or date_to):
            match_stage["processed_time"] = {}
            if date_from:
                match_stage["processed_time"]["$gte"] = date_from
            if date_to:
                match_stage["processed_time"]["$lte"] = date_to

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.extend([
            {"$unwind": "$category"},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ])

        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append({"category": doc["_id"], "count": doc["count"]})
        return results

    async def find_similar_article(self, title: str, hours_window: int = 48) -> Optional[dict]:
        """
        Find a processed article within the last N hours with a highly similar title.

        Two-phase strategy (Flaw 5 fix):
          Phase 1 — MongoDB $text search uses the title text index to retrieve
                    at most 20 candidates (O(log N) index scan, server-side).
          Phase 2 — SequenceMatcher runs only on those ≤20 candidates in Python.

        Requires index (run once via migration/seed):
            db.processed_data.create_index([("title", "text")])
        """
        time_limit = datetime.utcnow() - timedelta(hours=hours_window)

        # Extract meaningful search terms: words longer than 3 chars, capped at 60 chars
        search_terms = " ".join(w for w in title.split() if len(w) > 3)[:60]

        if search_terms:
            # Phase 1: text-index pre-filter — server returns only relevant candidates
            pipeline = [
                {
                    "$match": {
                        "$text": {"$search": search_terms},
                        "is_relevant": {"$ne": False},
                        "publish_time": {"$gte": time_limit},
                    }
                },
                {"$addFields": {"_score": {"$meta": "textScore"}}},
                {"$sort": {"_score": -1}},
                {"$limit": 20},
                {"$project": {"title": 1, "_id": 1}},
            ]
            cursor = self.collection.aggregate(pipeline)
        else:
            # Fallback for very short titles: time-window scan limited to 20 docs
            cursor = self.collection.find(
                {"is_relevant": {"$ne": False}, "publish_time": {"$gte": time_limit}},
                {"title": 1},
            ).sort("publish_time", -1).limit(20)

        # Phase 2: SequenceMatcher on at most 20 candidates
        t1 = title.lower().strip().replace('"', "").replace("'", "")
        best_id = None
        highest_similarity = 0.0

        async for doc in cursor:
            t2 = doc.get("title", "").lower().strip().replace('"', "").replace("'", "")
            similarity = SequenceMatcher(None, t1, t2).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_id = doc["_id"]

        if highest_similarity >= 0.68 and best_id is not None:
            # Fetch full document only on confirmed match
            full_doc = await self.collection.find_one({"_id": best_id})
            return _serialize_doc(full_doc)
        return None

    async def add_citation(self, processed_id: str, citation: dict) -> bool:
        """
        Atomically append a citation if the source URL is not already present.

        Single round-trip: MongoDB evaluates the array dedup condition server-side
        and performs the $push in one atomic update_one call (Flaw 6 fix).

        Note on self-healing migration: old documents without a citations array
        are handled by a dedicated one-time migration script, not here.
        """
        result = await self.collection.update_one(
            {
                "_id": ObjectId(processed_id),
                # Only match documents where this source_url is NOT already cited
                "citations.source_url": {"$ne": citation["source_url"]},
            },
            {"$push": {"citations": citation}},
        )
        # modified_count == 0 means either doc missing or URL already present — both OK
        return result.modified_count > 0


class AlertRuleRepository:
    """MongoDB repository for AlertRules collection."""


    @property
    def collection(self):
        return MongoDB.get_db().alert_rules

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active(self) -> list[dict]:
        cursor = self.collection.find({"is_active": True})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def create(self, data: dict) -> dict:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        update_data = {k: v for k, v in data.items() if v is not None}
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )
        return await self.find_by_id(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self.collection.count_documents({})


class LLMConfigRepository:
    """MongoDB repository for LLMConfig collection."""

    @property
    def collection(self):
        return MongoDB.get_db().llm_configs

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active(self) -> list[dict]:
        cursor = self.collection.find({"is_active": True})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active_by_model(self, model_name: str) -> list[dict]:
        cursor = self.collection.find({"is_active": True, "model_name": model_name})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_default_configs(self) -> list[dict]:
        """Find active configurations of the default model."""
        # First find a config marked as default
        default_doc = await self.collection.find_one({"is_active": True, "is_default": True})
        if not default_doc:
            # If none, return any active keys for the default model (e.g. gemini-3.5-flash)
            cursor = self.collection.find({"is_active": True, "model_name": "gemini-3.5-flash"})
            results = [_serialize_doc(doc) async for doc in cursor]
            if not results:
                # Fallback to any active model configuration
                cursor = self.collection.find({"is_active": True})
                results = [_serialize_doc(doc) async for doc in cursor]
            return results
        
        # If we have a default model, find all active keys for that model
        cursor = self.collection.find({"is_active": True, "model_name": default_doc["model_name"]})
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def create(self, data: dict) -> dict:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        if data.get("is_default"):
            # Ensure other configurations are not marked as default
            await self.collection.update_many({}, {"$set": {"is_default": False}})
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        update_data = {k: v for k, v in data.items() if v is not None}
        if update_data.get("is_default"):
            # Ensure other configurations are not marked as default
            await self.collection.update_many({"_id": {"$ne": ObjectId(id)}}, {"$set": {"is_default": False}})
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )
        return await self.find_by_id(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def set_default_model(self, model_name: str) -> bool:
        """Set all configurations for a specific model_name as default."""
        await self.collection.update_many({}, {"$set": {"is_default": False}})
        await self.collection.update_many({"model_name": model_name}, {"$set": {"is_default": True}})
        return True


class CrawlerSettingsRepository:
    """MongoDB repository for crawler frequency settings."""

    @property
    def collection(self):
        return MongoDB.get_db().crawler_settings

    async def get_settings(self) -> dict:
        """Get crawler settings, returns default settings if none found."""
        doc = await self.collection.find_one({"_id": "crawler_settings"})
        if not doc:
            # Default settings
            default_settings = {
                "_id": "crawler_settings",
                "is_enabled": True,
                "frequency_type": "interval",
                "interval_minutes": 60,
                "fixed_hours": ["07:00", "10:00", "12:00"],
                "hourly_range": {
                    "start_hour": 7,
                    "end_hour": 19,
                    "interval_hours": 1
                },
                "updated_at": datetime.utcnow()
            }
            await self.collection.insert_one(default_settings)
            return default_settings
        return _serialize_doc(doc)

    async def update_settings(self, data: dict) -> dict:
        """Update crawler settings."""
        data["updated_at"] = datetime.utcnow()
        # Remove _id if present in update payload to prevent modification error
        update_data = {k: v for k, v in data.items() if k != "_id"}
        await self.collection.update_one(
            {"_id": "crawler_settings"},
            {"$set": update_data},
            upsert=True
        )
        return await self.get_settings()


class GeneralSettingsRepository:
    """MongoDB repository for general application settings."""

    @property
    def collection(self):
        return MongoDB.get_db().general_settings

    async def get_settings(self) -> dict:
        """Get settings, returns default settings if none found."""
        doc = await self.collection.find_one({"_id": "general_settings"})
        if not doc:
            default_settings = {
                "_id": "general_settings",
                "pin_enabled": True,
                "pin_code": "2026",
                "updated_at": datetime.utcnow()
            }
            await self.collection.insert_one(default_settings)
            return default_settings
        return _serialize_doc(doc)

    async def update_settings(self, data: dict) -> dict:
        """Update settings."""
        data["updated_at"] = datetime.utcnow()
        # Remove _id if present in update payload to prevent modification error
        update_data = {k: v for k, v in data.items() if k != "_id"}
        await self.collection.update_one(
            {"_id": "general_settings"},
            {"$set": update_data},
            upsert=True
        )
        return await self.get_settings()


class LLMPromptRepository:
    """MongoDB repository for LLMPrompt collection."""

    @property
    def collection(self):
        return MongoDB.get_db().llm_prompts

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [_serialize_doc(doc) async for doc in cursor]

    async def find_active(self) -> Optional[dict]:
        """Find the active prompt configuration."""
        doc = await self.collection.find_one({"is_active": True})
        return _serialize_doc(doc) if doc else None

    async def find_by_id(self, id: str) -> Optional[dict]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return _serialize_doc(doc) if doc else None

    async def create(self, data: dict) -> dict:
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        if data.get("is_active"):
            # Ensure other configurations are not marked as active
            await self.collection.update_many({}, {"$set": {"is_active": False}})
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        update_data = {k: v for k, v in data.items() if v is not None}
        if update_data.get("is_active"):
            # Ensure other configurations are not marked as active
            await self.collection.update_many({"_id": {"$ne": ObjectId(id)}}, {"$set": {"is_active": False}})
        await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )
        return await self.find_by_id(id)

    async def set_active(self, id: str) -> Optional[dict]:
        """Set a specific prompt as active and others as inactive."""
        await self.collection.update_many({"_id": {"$ne": ObjectId(id)}}, {"$set": {"is_active": False}})
        await self.collection.update_one({"_id": ObjectId(id)}, {"$set": {"is_active": True, "updated_at": datetime.utcnow()}})
        return await self.find_by_id(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self) -> int:
        return await self.collection.count_documents({})

