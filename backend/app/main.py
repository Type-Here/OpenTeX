"""
Entry point FastAPI per OpenTeX.

Stack: FastAPI + Motor (async) + MongoDB 8.0
Paradigma CAP: AP  |  Consistenza: BASE / eventual consistency
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import get_database, ping_database
from app.routers.auth import router as auth_router
from app.routers.stats import router as stats_router
from app.routers.permissions import router as permissions_router
from app.routers.projects import router as projects_router
from app.routers.users import router as users_router

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
    else:
        db = get_database()
        await db["users"].create_index("email", unique=True)
        logger.info("Unique index on users.email ensured.")
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


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(stats_router, prefix="/stats", tags=["stats"])

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # When detail is a dict (e.g. 403 with role info), return it flat — not nested under "detail".
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(permissions_router, prefix="/projects", tags=["permissions"])


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
