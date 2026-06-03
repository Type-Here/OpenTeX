from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_database

router = APIRouter()

_USERS = "users"


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    department: str

    @classmethod
    def from_mongo(cls, doc: dict) -> "UserResponse":
        return cls(
            id=str(doc["_id"]),
            first_name=doc.get("first_name", ""),
            last_name=doc.get("last_name", ""),
            email=doc.get("email", ""),
            department=doc.get("department", ""),
        )


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        raise HTTPException(status_code=422, detail=f"Invalid ObjectId: {value!r}")


@router.get("/", response_model=list[UserResponse])
async def list_users():
    db = get_database()
    cursor = db[_USERS].find({}).sort("last_name", 1)
    return [UserResponse.from_mongo(doc) async for doc in cursor]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    db = get_database()
    doc = await db[_USERS].find_one({"_id": _oid(user_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_mongo(doc)
