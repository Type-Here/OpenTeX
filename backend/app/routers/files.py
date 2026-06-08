from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.dependencies import get_current_user
from app.models.file import FileResponse, FileUpdate
from app.models.permissions import Role
from app.services import permissions_service

router = APIRouter()

_FILES = "files"


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


@router.put("/{file_id}", response_model=FileResponse)
async def update_file_content(
    file_id: str,
    body: FileUpdate,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    doc = await db[_FILES].find_one({"_id": _oid(file_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="File not found")
    if doc.get("file_type") not in ("tex", "bib"):
        raise HTTPException(status_code=422, detail="Only tex/bib files have editable content")

    project_id = str(doc["project_id"])
    await permissions_service.require_access(db, current_user, project_id, Role.EDITOR)

    updated = await db[_FILES].find_one_and_update(
        {"_id": doc["_id"]},
        {"$set": {"content": body.content, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    return FileResponse.from_mongo(updated)


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    doc = await db[_FILES].find_one({"_id": _oid(file_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="File not found")
    project_id = str(doc["project_id"])
    await permissions_service.require_access(db, current_user, project_id, Role.EDITOR)
    await db[_FILES].delete_one({"_id": doc["_id"]})