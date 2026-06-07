from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUpdate(BaseModel):
    content: str


class FileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    created_at: datetime
    content: Optional[str] = None
    path: Optional[str] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_mongo(cls, doc: dict) -> "FileResponse":
        return cls(
            id=str(doc["_id"]),
            project_id=str(doc["project_id"]),
            filename=doc["filename"],
            file_type=doc["file_type"],
            created_at=doc["created_at"],
            content=doc.get("content"),
            path=doc.get("path"),
            updated_at=doc.get("updated_at"),
        )
