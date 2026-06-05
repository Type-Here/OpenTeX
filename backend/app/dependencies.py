from bson import ObjectId
from fastapi import Header, HTTPException

from app.database import get_database


async def get_current_user(x_user_id: str = Header(...)) -> str:
    if not ObjectId.is_valid(x_user_id):
        raise HTTPException(status_code=401, detail="X-User-Id must be a valid ObjectId")
    return x_user_id


async def get_admin_user(x_user_id: str = Header(...)) -> str:
    if not ObjectId.is_valid(x_user_id):
        raise HTTPException(status_code=401, detail="X-User-Id must be a valid ObjectId")
    db = get_database()
    user = await db["users"].find_one({"_id": ObjectId(x_user_id)})
    if user is None or not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return x_user_id
