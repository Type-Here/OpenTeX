"""
LaTeX compilation endpoint (Issue #21).
Each request runs Tectonic in an isolated temp directory.
Concurrency is limited by a module-level asyncio.Semaphore.

The pipeline is instrumented: the database, filesystem and compiler phases are
timed separately so they can be reported by GET /stats/compile-benchmark.
"""

import asyncio
import logging
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.database import get_database
from app.dependencies import get_current_user
from app.models.permissions import Role
from app.services import permissions_service

router = APIRouter()
logger = logging.getLogger(__name__)

_PROJECTS = "projects"
_FILES = "files"
_SEMAPHORE = asyncio.Semaphore(2)
_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class CompileTimings:
    """Wall-clock duration of each compilation phase, in milliseconds."""

    db_ms: float
    io_ms: float
    tex_ms: float

    @property
    def total_ms(self) -> float:
        return self.db_ms + self.io_ms + self.tex_ms


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


def _pick_main(files: list[dict]) -> dict:
    """Return the entry-point .tex file: prefer main.tex, else first .tex alphabetically."""
    for f in files:
        if f["filename"] == "main.tex":
            return f
    tex = sorted([f for f in files if f["file_type"] == "tex"], key=lambda f: f["filename"])
    if not tex:
        raise HTTPException(status_code=422, detail="No .tex source files found in this project")
    return tex[0]


async def run_compilation(db, oid: ObjectId) -> tuple[bytes, str, CompileTimings]:
    """
    Compile a project's LaTeX sources and return (pdf_bytes, stem, timings).

    Assumes the project exists and the caller is authorised. Raises the same
    HTTPExceptions as the endpoint (422 / 500 / 504) so both callers behave
    identically.
    """
    # ── Phase 1: fetch the compilable sources (tex/bib with content in Mongo)
    t0 = time.perf_counter()
    source_files = [
        doc async for doc in db[_FILES].find(
            {"project_id": oid, "file_type": {"$in": ["tex", "bib"]}}
        )
        if doc.get("content")
    ]
    db_ms = (time.perf_counter() - t0) * 1000

    if not source_files:
        raise HTTPException(status_code=422, detail="No compilable source files found in this project")

    main_file = _pick_main(source_files)

    async with _SEMAPHORE:
        tmpdir = Path(tempfile.mkdtemp(prefix=f"opentex_{uuid.uuid4().hex}_"))
        try:
            # ── Phase 2: write the sources into the isolated temp directory
            t0 = time.perf_counter()
            for f in source_files:
                (tmpdir / f["filename"]).write_text(f["content"], encoding="utf-8")
            io_ms = (time.perf_counter() - t0) * 1000

            main_path = tmpdir / main_file["filename"]

            # ── Phase 3: run the Tectonic subprocess
            t0 = time.perf_counter()
            try:
                proc = await asyncio.create_subprocess_exec(
                    "tectonic",
                    "--keep-logs",
                    "--outdir", str(tmpdir),
                    str(main_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(tmpdir),
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise HTTPException(status_code=504, detail="Compilation timed out")
            except FileNotFoundError:
                raise HTTPException(status_code=500, detail="Tectonic compiler not found on this server")
            tex_ms = (time.perf_counter() - t0) * 1000

            timings = CompileTimings(db_ms=db_ms, io_ms=io_ms, tex_ms=tex_ms)
            logger.info(
                "Compile %s — db=%.2f ms | io=%.2f ms | tex=%.2f ms | total=%.2f ms",
                oid, timings.db_ms, timings.io_ms, timings.tex_ms, timings.total_ms,
            )

            if proc.returncode == 0:
                pdf_path = tmpdir / f"{main_path.stem}.pdf"
                if not pdf_path.exists():
                    raise HTTPException(status_code=500, detail="Compilation succeeded but PDF not produced")
                return pdf_path.read_bytes(), main_path.stem, timings

            # Compilation failed — prefer the .log file, fall back to stderr
            log_path = tmpdir / f"{main_path.stem}.log"
            log_text = (
                log_path.read_text(encoding="utf-8", errors="replace")
                if log_path.exists()
                else stderr.decode(errors="replace")
            )
            raise HTTPException(
                status_code=422,
                detail={"error": "Compilation failed", "log": log_text},
            )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


@router.post(
    "/{project_id}/compile",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Compiled PDF"},
        422: {"description": "Compilation failed — error log in response body"},
    },
    summary="Compile project LaTeX sources",
)
async def compile_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    oid = _oid(project_id)

    if await db[_PROJECTS].find_one({"_id": oid}) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await permissions_service.require_access(db, current_user, project_id, Role.VIEWER)

    pdf_bytes, stem, _ = await run_compilation(db, oid)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'},
    )