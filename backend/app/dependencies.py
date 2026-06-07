from fastapi import Header, HTTPException

from app.security import decode_access_token


def _extract_user_id(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")
    token = authorization[len("Bearer "):]
    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_id


async def get_current_user(authorization: str = Header(...)) -> str:
    return _extract_user_id(authorization)


async def get_admin_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")
    token = authorization[len("Bearer "):]
    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    if not payload.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id