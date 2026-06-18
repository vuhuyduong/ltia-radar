"""
MongoDB Repository implementations — CRUD operations for all collections.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

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
    ) -> list[dict]:
        """Find processed articles with optional filters."""
        query: dict = {}

        if sentiment:
            query["sentiment"] = sentiment
        if impact_level:
            query["impact_level"] = impact_level
        if category:
            query["category"] = {"$in": [category]}
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
            .sort("processed_time", -1)
            .skip(skip)
            .limit(limit)
        )
        return [_serialize_doc(doc) async for doc in cursor]

    async def count(self, query: Optional[dict] = None) -> int:
        return await self.collection.count_documents(query or {})

    async def get_sentiment_distribution(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict]:
        """Aggregate sentiment counts for pie chart."""
        match_stage: dict = {}
        if date_from or date_to:
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
    ) -> list[dict]:
        """Aggregate article counts by date for timeline chart."""
        match_stage: dict = {}
        if date_from or date_to:
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
                                "date": "$processed_time",
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

    async def get_top_risks(self, limit: int = 10) -> list[dict]:
        """Get top N highest risk articles (CRITICAL first, then HIGH)."""
        # Define priority order
        pipeline = [
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
            {"$sort": {"impact_order": 1, "processed_time": -1}},
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
    ) -> list[dict]:
        """Aggregate category counts for bar chart."""
        match_stage: dict = {}
        if date_from or date_to:
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
