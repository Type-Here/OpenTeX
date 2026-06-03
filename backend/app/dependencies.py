from bson import ObjectId
from fastapi import Header, HTTPException


async def get_current_user(x_user_id: str = Header(...)) -> str:
    if not ObjectId.is_valid(x_user_id):
        raise HTTPException(status_code=401, detail="X-User-Id must be a valid ObjectId")
    return x_user_id
