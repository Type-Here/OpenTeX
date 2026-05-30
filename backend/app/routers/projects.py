from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pymongo import ReturnDocument

from app.database import get_database
from app.models.file import FileResponse
from app.models.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()

_PROJECTS = "projects"
_FILES = "files"


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate):
    db = get_database()
    doc = {
        "title": body.title,
        "abstract": body.abstract,
        "owner_id": ObjectId(body.owner_id),
        "tags": body.tags,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db[_PROJECTS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return ProjectResponse.from_mongo(doc)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(owner_id: Optional[str] = Query(default=None)):
    db = get_database()
    filt: dict = {}
    if owner_id is not None:
        filt["owner_id"] = _oid(owner_id)
    cursor = db[_PROJECTS].find(filt)
    return [ProjectResponse.from_mongo(doc) async for doc in cursor]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    db = get_database()
    doc = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.from_mongo(doc)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: ProjectUpdate):
    db = get_database()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided for update")
    updates["updated_at"] = datetime.now(timezone.utc)
    doc = await db[_PROJECTS].find_one_and_update(
        {"_id": _oid(project_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.from_mongo(doc)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    db = get_database()
    result = await db[_PROJECTS].delete_one({"_id": _oid(project_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/files", response_model=list[FileResponse])
async def list_project_files(project_id: str):
    db = get_database()
    oid = _oid(project_id)
    if await db[_PROJECTS].find_one({"_id": oid}) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    cursor = db[_FILES].find({"project_id": oid})
    return [FileResponse.from_mongo(doc) async for doc in cursor]
