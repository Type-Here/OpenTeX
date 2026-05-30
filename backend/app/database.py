"""
Connessione asincrona a MongoDB via Motor.

Architettura AP (Availability + Partition Tolerance, teorema CAP) con semantica BASE.
Le operazioni sono atomiche a singolo documento; le JOIN vengono eseguite via $lookup
nelle aggregation pipeline.
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
        logger.info("Motor client creato — URI: %s", settings.mongo_uri.split("@")[-1])
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
