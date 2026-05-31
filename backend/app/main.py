"""
Entry point FastAPI per OpenTeX.

Stack: FastAPI + Motor (async) + MongoDB 8.0
Paradigma CAP: AP  |  Consistenza: BASE / eventual consistency
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import ping_database
from app.routers.stats import router as stats_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OpenTeX backend avvio...")
    ok = await ping_database()
    if not ok:
        logger.warning("MongoDB non raggiungibile all'avvio — verificare la connessione.")
    yield
    logger.info("OpenTeX backend shutdown.")


app = FastAPI(
    title="OpenTeX API",
    description=(
        "Backend REST per OpenTeX — ambiente collaborativo LaTeX self-hosted. "
        "MongoDB 8.0, paradigma AP/BASE."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(stats_router, prefix="/stats", tags=["stats"])


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    mongo_ok = await ping_database()
    return {
        "status": "ok" if mongo_ok else "degraded",
        "mongo": "connected" if mongo_ok else "unreachable",
        "debug": settings.debug,
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"project": "OpenTeX", "version": "0.1.0", "docs": "/docs"}
