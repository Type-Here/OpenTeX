from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.dependencies import get_current_user
from app.models.permissions import PermissionAssign, PermissionResponse, Role
from app.services import permissions_service

router = APIRouter()

_PERMISSIONS = "permissions"
_PROJECTS = "projects"


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


@router.post("/{project_id}/permissions", response_model=PermissionResponse)
async def assign_permission(
    project_id: str,
    body: PermissionAssign,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    if await db[_PROJECTS].find_one({"_id": _oid(project_id)}) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    doc = await permissions_service.assign_permission(
        db, project_id, body.user_id, body.role, current_user
    )
    return PermissionResponse.from_mongo(doc)


@router.delete("/{project_id}/permissions/{user_id}", status_code=200)
async def revoke_permission(
    project_id: str,
    user_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    found = await permissions_service.revoke_permission(db, project_id, user_id, current_user)
    if not found:
        raise HTTPException(status_code=404, detail="Permission not found")
    return {"detail": "Permission revoked"}


@router.get("/{project_id}/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    project_id: str,
    current_user: str = Depends(get_current_user),
):
    db = get_database()
    if await db[_PROJECTS].find_one({"_id": _oid(project_id)}) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await permissions_service.require_access(db, current_user, project_id, Role.VIEWER)
    cursor = db[_PERMISSIONS].find({"project_id": _oid(project_id)})
    return [PermissionResponse.from_mongo(doc) async for doc in cursor]
