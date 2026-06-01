from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo import ReturnDocument

from app.models.permissions import Role, ROLE_HIERARCHY

_PROJECTS = "projects"
_PERMISSIONS = "permissions"
_USERS = "users"


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


async def get_user_role(db, user_id: str, project_id: str) -> Role | None:
    project = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if project is None:
        return None
    if str(project["owner_id"]) == user_id:
        return Role.ADMIN
    perm = await db[_PERMISSIONS].find_one({
        "user_id": _oid(user_id),
        "project_id": _oid(project_id),
    })
    if perm is None:
        return None
    return Role(perm["role"])


async def check_access(db, user_id: str, project_id: str, required_role: Role) -> bool:
    role = await get_user_role(db, user_id, project_id)
    if role is None:
        return False
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[required_role]


async def require_access(db, user_id: str, project_id: str, required_role: Role) -> None:
    """Raises HTTP 403 with flat body if the user lacks the required role."""
    role = await get_user_role(db, user_id, project_id)
    if role is None or ROLE_HIERARCHY[role] < ROLE_HIERARCHY[required_role]:
        raise _access_denied(required_role, role)


def _access_denied(required_role: Role, actual_role: Role | None) -> HTTPException:
    # Store the flat body in detail as a dict; main.py exception handler
    # returns dicts unwrapped so the response body is flat (not nested under "detail").
    return HTTPException(
        status_code=403,
        detail={
            "detail": "Access denied: insufficient permissions",
            "required_role": required_role.value,
            "your_role": actual_role.value if actual_role else "none",
        },
    )


async def assign_permission(
    db,
    project_id: str,
    target_user_id: str,
    role: Role,
    requesting_user_id: str,
) -> dict:
    await require_access(db, requesting_user_id, project_id, Role.ADMIN)

    project = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if str(project["owner_id"]) == target_user_id:
        raise HTTPException(status_code=400, detail="Owner already has implicit Admin role")

    if await db[_USERS].find_one({"_id": _oid(target_user_id)}) is None:
        raise HTTPException(status_code=404, detail="Target user not found")

    now = datetime.now(timezone.utc)
    doc = await db[_PERMISSIONS].find_one_and_update(
        {"user_id": _oid(target_user_id), "project_id": _oid(project_id)},
        {"$set": {
            "role": role.value,
            "granted_at": now,
            "granted_by": _oid(requesting_user_id),
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc


async def revoke_permission(
    db,
    project_id: str,
    target_user_id: str,
    requesting_user_id: str,
) -> bool:
    await require_access(db, requesting_user_id, project_id, Role.ADMIN)

    project = await db[_PROJECTS].find_one({"_id": _oid(project_id)})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if str(project["owner_id"]) == target_user_id:
        raise HTTPException(status_code=400, detail="Cannot revoke owner's access")

    result = await db[_PERMISSIONS].delete_one({
        "user_id": _oid(target_user_id),
        "project_id": _oid(project_id),
    })
    return result.deleted_count > 0
