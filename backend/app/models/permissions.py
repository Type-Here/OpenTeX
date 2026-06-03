from datetime import datetime
from enum import Enum
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, field_validator


class Role(str, Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    VIEWER = "Viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN: 3,
    Role.EDITOR: 2,
    Role.VIEWER: 1,
}


class PermissionAssign(BaseModel):
    user_id: str
    role: Role

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not ObjectId.is_valid(v):
            raise ValueError("user_id must be a valid 24-char hex ObjectId")
        return v


class PermissionResponse(BaseModel):
    id: str
    user_id: str
    project_id: str
    role: Role
    granted_at: datetime
    granted_by: Optional[str] = None

    @classmethod
    def from_mongo(cls, doc: dict) -> "PermissionResponse":
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            project_id=str(doc["project_id"]),
            role=Role(doc["role"]),
            granted_at=doc["granted_at"],
            granted_by=str(doc["granted_by"]) if doc.get("granted_by") else None,
        )
