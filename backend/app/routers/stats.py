import time
from datetime import datetime
from typing import Optional

import pymongo
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import OperationFailure

from app.database import get_database
from app.dependencies import get_admin_user
from app.models.stats import BenchmarkResult, DepartmentStat

router = APIRouter()

_PROJECTS = "projects"

# ── Aggregation stats ────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[DepartmentStat])
async def project_stats(
    department: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    _: str = Depends(get_admin_user),
):
    db = get_database()
    pipeline = _build_pipeline(department, date_from, date_to)
    cursor = db[_PROJECTS].aggregate(pipeline)
    return [DepartmentStat(**doc) async for doc in cursor]


def _build_pipeline(department, date_from, date_to):
    pipeline: list[dict] = []

    date_filter: dict = {}
    if date_from:
        date_filter["$gte"] = date_from
    if date_to:
        date_filter["$lte"] = date_to
    if date_filter:
        pipeline.append({"$match": {"created_at": date_filter}})

    pipeline.append({"$lookup": {"from": "users", "localField": "owner_id", "foreignField": "_id", "as": "owner"}})
    pipeline.append({"$unwind": "$owner"})

    if department:
        pipeline.append({"$match": {"owner.department": department}})

    pipeline.append({"$lookup": {"from": "permissions", "localField": "_id", "foreignField": "project_id", "as": "permissions"}})
    pipeline.append({"$lookup": {"from": "activity_logs", "localField": "_id", "foreignField": "project_id", "as": "activity_logs"}})
    pipeline.append({"$addFields": {"collaborator_count": {"$size": "$permissions"}, "activity_count": {"$size": "$activity_logs"}}})
    pipeline.append({"$group": {"_id": "$owner.department", "project_count": {"$sum": 1}, "total_collaborators": {"$sum": "$collaborator_count"}, "avg_collaborators": {"$avg": "$collaborator_count"}, "total_activity": {"$sum": "$activity_count"}}})
    pipeline.append({"$sort": {"total_activity": -1}})
    pipeline.append({"$project": {"_id": 0, "department": "$_id", "project_count": 1, "total_collaborators": 1, "avg_collaborators": {"$round": ["$avg_collaborators", 2]}, "total_activity": 1}})

    return pipeline


# ── Benchmarks ───────────────────────────────────────────────────────────────

_N_RUNS = 10

_INDEX_DEFS: dict[str, tuple[str, list]] = {
    "projects_text_search": (
        "projects",
        [("title", pymongo.TEXT), ("abstract", pymongo.TEXT)],
    ),
    "projects_owner_date": (
        "projects",
        [("owner_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
    ),
    "permissions_project_id": (
        "permissions",
        [("project_id", pymongo.ASCENDING)],
    ),
    "activity_logs_project_id": (
        "activity_logs",
        [("project_id", pymongo.ASCENDING)],
    ),
    "files_project_id": (
        "files",
        [("project_id", pymongo.ASCENDING)],
    ),
}


async def _avg_ms(coro_fn, n: int) -> float:
    total = 0.0
    for _ in range(n):
        t0 = time.perf_counter()
        await coro_fn()
        total += (time.perf_counter() - t0) * 1000
    return total / n


async def _bench_one(db, label: str, index_name: str, with_fn, without_fn) -> dict:
    collection, spec = _INDEX_DEFS[index_name]

    await with_fn()
    avg_with = await _avg_ms(with_fn, _N_RUNS)

    try:
        await db[collection].drop_index(index_name)
    except OperationFailure:
        # Index doesn't exist — report timings with index only, mark without as N/A
        return {"label": label, "with_ms": round(avg_with, 3), "without_ms": -1.0, "speedup": -1.0}

    try:
        await without_fn()
        avg_without = await _avg_ms(without_fn, _N_RUNS)
    finally:
        await db[collection].create_index(spec, name=index_name)

    speedup = avg_without / avg_with if avg_with > 0 else 0.0
    return {
        "label": label,
        "with_ms": round(avg_with, 3),
        "without_ms": round(avg_without, 3),
        "speedup": round(speedup, 1),
    }


async def _ensure_indexes(db) -> None:
    """Create all benchmark indexes if they don't already exist (idempotent)."""
    for index_name, (collection, spec) in _INDEX_DEFS.items():
        try:
            await db[collection].create_index(spec, name=index_name)
        except OperationFailure:
            pass  # already exists with same name/spec — safe to ignore


@router.get("/benchmarks", response_model=list[BenchmarkResult])
async def run_benchmarks(_: str = Depends(get_admin_user)):
    db = get_database()

    try:
        project = await db["projects"].find_one({}, {"_id": 1, "owner_id": 1})
    except OperationFailure as e:
        raise HTTPException(status_code=422, detail=f"DB error: {e}")

    if project is None:
        raise HTTPException(status_code=422, detail="No data in DB — run the seed script first.")

    # Create any missing indexes before benchmarking (mirrors create_indexes.py)
    await _ensure_indexes(db)

    owner_id = project["owner_id"]
    project_id = project["_id"]

    benchmarks = [
        (
            "Text search (title + abstract)",
            "projects_text_search",
            lambda: db["projects"].count_documents({"$text": {"$search": "latex"}}),
            lambda: db["projects"].count_documents({"$or": [
                {"title":    {"$regex": "latex", "$options": "i"}},
                {"abstract": {"$regex": "latex", "$options": "i"}},
            ]}),
        ),
        (
            "Compound: owner_id + created_at sort",
            "projects_owner_date",
            lambda: db["projects"].count_documents({"owner_id": owner_id}),
            lambda: db["projects"].count_documents({"owner_id": owner_id}),
        ),
        (
            "Permissions by project_id",
            "permissions_project_id",
            lambda: db["permissions"].count_documents({"project_id": project_id}),
            lambda: db["permissions"].count_documents({"project_id": project_id}),
        ),
        (
            "Activity logs by project_id",
            "activity_logs_project_id",
            lambda: db["activity_logs"].count_documents({"project_id": project_id}),
            lambda: db["activity_logs"].count_documents({"project_id": project_id}),
        ),
        (
            "Files by project_id",
            "files_project_id",
            lambda: db["files"].count_documents({"project_id": project_id}),
            lambda: db["files"].count_documents({"project_id": project_id}),
        ),
    ]

    results = []
    for label, index_name, with_fn, without_fn in benchmarks:
        try:
            result = await _bench_one(db, label, index_name, with_fn, without_fn)
        except OperationFailure as e:
            # Recreate index if something went wrong mid-benchmark
            collection, spec = _INDEX_DEFS[index_name]
            try:
                await db[collection].create_index(spec, name=index_name)
            except OperationFailure:
                pass
            result = {"label": label, "with_ms": -1.0, "without_ms": -1.0, "speedup": -1.0}
        results.append(BenchmarkResult(**result))

    return results
