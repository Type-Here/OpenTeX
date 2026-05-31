from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, field_validator


class ProjectCreate(BaseModel):
    title: str
    abstract: str
    owner_id: str
    tags: list[str] = []

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v: str) -> str:
        if not ObjectId.is_valid(v):
            raise ValueError("owner_id must be a valid 24-char hex ObjectId")
        return v


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    tags: Optional[list[str]] = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    abstract: str
    owner_id: str
    tags: list[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_mongo(cls, doc: dict) -> "ProjectResponse":
        return cls(
            id=str(doc["_id"]),
            title=doc["title"],
            abstract=doc["abstract"],
            owner_id=str(doc["owner_id"]),
            tags=doc.get("tags", []),
            created_at=doc["created_at"],
            updated_at=doc.get("updated_at"),
        )
