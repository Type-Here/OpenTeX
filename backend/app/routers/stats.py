from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.database import get_database
from app.models.stats import DepartmentStat

router = APIRouter()

_PROJECTS = "projects"


@router.get("/projects", response_model=list[DepartmentStat])
async def project_stats(
    department: Optional[str] = Query(default=None, description="Filter by owner department"),
    date_from: Optional[datetime] = Query(default=None, description="Filter projects created from this date (ISO 8601)"),
    date_to: Optional[datetime] = Query(default=None, description="Filter projects created up to this date (ISO 8601)"),
):
    """
    Aggregation pipeline across 4 collections: projects → users → permissions → activity_logs.
    Returns collaboration and activity statistics grouped by owner department, sorted by
    total activity descending.
    """
    db = get_database()
    pipeline = _build_pipeline(department, date_from, date_to)
    cursor = db[_PROJECTS].aggregate(pipeline)
    return [DepartmentStat(**doc) async for doc in cursor]


def _build_pipeline(
    department: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> list[dict]:
    pipeline: list[dict] = []

    # $match early: filter projects by creation date before any $lookup
    # keeps the working set small for the subsequent joins
    date_filter: dict = {}
    if date_from:
        date_filter["$gte"] = date_from
    if date_to:
        date_filter["$lte"] = date_to
    if date_filter:
        pipeline.append({"$match": {"created_at": date_filter}})

    # JOIN 1: projects → users (resolve owner, get department)
    pipeline.append({
        "$lookup": {
            "from": "users",
            "localField": "owner_id",
            "foreignField": "_id",
            "as": "owner",
        }
    })
    # $unwind: owner is a 1-element array after $lookup; flatten to object
    pipeline.append({"$unwind": "$owner"})

    # optional department filter applied after owner is resolved
    if department:
        pipeline.append({"$match": {"owner.department": department}})

    # JOIN 2: projects → permissions (all collaborators for each project)
    pipeline.append({
        "$lookup": {
            "from": "permissions",
            "localField": "_id",
            "foreignField": "project_id",
            "as": "permissions",
        }
    })

    # JOIN 3: projects → activity_logs (all events for each project)
    pipeline.append({
        "$lookup": {
            "from": "activity_logs",
            "localField": "_id",
            "foreignField": "project_id",
            "as": "activity_logs",
        }
    })

    # $addFields: compute per-project counts before grouping
    pipeline.append({
        "$addFields": {
            "collaborator_count": {"$size": "$permissions"},
            "activity_count": {"$size": "$activity_logs"},
        }
    })

    # $group: roll up by department with accumulators
    pipeline.append({
        "$group": {
            "_id": "$owner.department",
            "project_count": {"$sum": 1},
            "total_collaborators": {"$sum": "$collaborator_count"},
            "avg_collaborators": {"$avg": "$collaborator_count"},
            "total_activity": {"$sum": "$activity_count"},
        }
    })

    # $sort: most active departments first
    pipeline.append({"$sort": {"total_activity": -1}})

    # $project: rename _id → department, round avg to 2 decimal places
    pipeline.append({
        "$project": {
            "_id": 0,
            "department": "$_id",
            "project_count": 1,
            "total_collaborators": 1,
            "avg_collaborators": {"$round": ["$avg_collaborators", 2]},
            "total_activity": 1,
        }
    })

    return pipeline