from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure

from app.database import get_database
from app.dependencies import get_current_user
from app.models.file import FileCreate, FileResponse
from app.models.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.models.permissions import Role
from app.services import permissions_service

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
async def list_projects(
    owner_id: Optional[str] = Query(default=None),
    member_id: Optional[str] = Query(default=None, description="Return projects where this user has an explicit permission entry"),
    q: Optional[str] = Query(
        default=None,
        description=(
            "Full-text search over title and abstract, served by the "
            "`projects_text_search` index. Matches whole words (stemmed), "
            "not partial prefixes. Results are sorted by relevance."
        ),
    ),
):
    db = get_database()
    query: dict = {}
    if member_id is not None:
        perms = await db["permissions"].find(
            {"user_id": _oid(member_id)}, {"project_id": 1}
        ).to_list(length=None)
        query["_id"] = {"$in": [p["project_id"] for p in perms]}
    elif owner_id is not None:
        query["owner_id"] = _oid(owner_id)

    search = q.strip() if q else ""
    if not search:
        cursor = db[_PROJECTS].find(query)
    else:
        # $text uses the projects_text_search index; the textScore meta field is
        # projected only to sort by relevance and is dropped by ProjectResponse.
        query["$text"] = {"$search": search}
        cursor = db[_PROJECTS].find(
            query, {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

    try:
        return [ProjectResponse.from_mongo(doc) async for doc in cursor]
    except OperationFailure as exc:
        # Code 27 = IndexNotFound: the text index is missing, which happens while
        # run_benchmark.py has it temporarily dropped. Report it as a transient
        # search outage instead of an opaque 500.
        if exc.code == 27:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Text search unavailable: the projects_text_search index is missing. "
                    "Run `python -m scripts.indexes.create_indexes` or restart the backend."
                ),
            )
        raise


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    doc = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await permissions_service.require_access(db, current_user, project_id, Role.VIEWER)
    return ProjectResponse.from_mongo(doc)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    await permissions_service.require_access(db, current_user, project_id, Role.EDITOR)
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
async def delete_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    project = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project["owner_id"]) != current_user:
        role = await permissions_service.get_user_role(db, current_user, project_id)
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Access denied: insufficient permissions",
                "required_role": "owner",
                "your_role": role.value if role else "none",
            },
        )
    await db[_PROJECTS].delete_one({"_id": _oid(project_id)})


@router.get("/{project_id}/files", response_model=list[FileResponse])
async def list_project_files(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    oid = _oid(project_id)
    if await db[_PROJECTS].find_one({"_id": oid}) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await permissions_service.require_access(db, current_user, project_id, Role.VIEWER)
    cursor = db[_FILES].find({"project_id": oid})
    return [FileResponse.from_mongo(doc) async for doc in cursor]


@router.post("/{project_id}/files", response_model=FileResponse, status_code=201)
async def create_project_file(
    project_id: str,
    body: FileCreate,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    oid = _oid(project_id)
    if await db[_PROJECTS].find_one({"_id": oid}) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await permissions_service.require_access(db, current_user, project_id, Role.EDITOR)
    existing = await db[_FILES].find_one({"project_id": oid, "filename": body.filename})
    if existing:
        raise HTTPException(status_code=409, detail=f"File '{body.filename}' already exists in this project")
    if body.file_type == "tex":
        initial_content = (
            "\\documentclass{article}\n\n"
            "\\title{" + body.filename.removesuffix(".tex") + "}\n"
            "\\author{}\n"
            "\\date{\\today}\n\n"
            "\\begin{document}\n\n"
            "\\maketitle\n\n"
            "\\section{Introduction}\n"
            "Start writing here.\n\n"
            "\\end{document}\n"
        )
    else:
        initial_content = ""

    doc = {
        "project_id": oid,
        "filename": body.filename,
        "file_type": body.file_type,
        "content": initial_content,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db[_FILES].insert_one(doc)
    doc["_id"] = result.inserted_id
    return FileResponse.from_mongo(doc)
