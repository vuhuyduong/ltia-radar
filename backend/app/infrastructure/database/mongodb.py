"""
MongoDB client singleton — Async connection using Motor.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings


class MongoDB:
    """Singleton MongoDB async client."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls):
        """Initialize MongoDB connection."""
        cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        cls.db = cls.client[settings.mongodb_database]

        # Create indexes
        await cls._create_indexes()

        print(f"✅ Connected to MongoDB: {settings.mongodb_database}")

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            print("🔌 Disconnected from MongoDB")

    @classmethod
    async def _create_indexes(cls):
        """Create required indexes for performance optimization."""
        if cls.db is None:
            return

        # RawData: Unique index on source_url for dedup
        await cls.db.raw_data.create_index("source_url", unique=True)
        await cls.db.raw_data.create_index("url_hash")
        await cls.db.raw_data.create_index("crawl_time")

        # ProcessedData: Compound index for dashboard queries (PRD Section 8.2)
        await cls.db.processed_data.create_index([
            ("target_scope", 1),
            ("impact_level", -1),
            ("processed_time", -1),
        ])
        await cls.db.processed_data.create_index("sentiment")
        await cls.db.processed_data.create_index("impact_level")
        await cls.db.processed_data.create_index("processed_time")
        
        # Text index on title for similarity deduplication
        await cls.db.processed_data.create_index([("title", "text")], name="title_text_idx")

        # Sources: Index on is_active for crawler queries
        await cls.db.sources.create_index("is_active")

        # Keywords: Index on is_active
        await cls.db.keywords.create_index("is_active")

        print("📑 MongoDB indexes created")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls.db is None:
            raise RuntimeError("MongoDB is not connected. Call MongoDB.connect() first.")
        return cls.db
