"""
Async MongoDB connection via Motor.

AP architecture (Availability + Partition Tolerance, CAP theorem) with BASE semantics.
Operations are atomic at the single-document level; JOINs are performed via $lookup
in aggregation pipelines.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
        logger.info("Motor client created — URI: %s", settings.mongo_uri.split("@")[-1])
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongo_db]


async def ping_database() -> bool:
    try:
        await get_client().admin.command("ping")
        logger.info("Ping MongoDB: OK")
        return True
    except Exception as exc:
        logger.error("Ping MongoDB FAILED: %s", exc)
        return False
