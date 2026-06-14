from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.routers.users import UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()

_USERS = "users"

DEPARTMENTS: list[str] = [
    "Informatica",
    "Ingegneria",
    "Matematica",
    "Fisica",
    "Chimica",
    "Biologia",
    "Medicina",
    "Economia",
    "Giurisprudenza",
    "Lettere e Filosofia",
    "Scienze Politiche",
    "Psicologia",
]


@router.get("/departments", response_model=list[str])
async def get_departments():
    return DEPARTMENTS


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    department: str

    @field_validator("department")
    @classmethod
    def department_must_be_valid(cls, v: str) -> str:
        if v not in DEPARTMENTS:
            raise ValueError(f"Invalid department. Allowed: {', '.join(DEPARTMENTS)}")
        return v


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterBody):
    db = get_database()
    existing = await db[_USERS].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "first_name": body.first_name,
        "last_name": body.last_name,
        "department": body.department,
        "is_admin": False,
    }
    try:
        result = await db[_USERS].insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc["_id"] = result.inserted_id
    return UserResponse.from_mongo(doc)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody):
    db = get_database()
    user = await db[_USERS].find_one({"email": body.email})
    if user is None or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["_id"]), "is_admin": bool(user.get("is_admin", False))})
    return TokenResponse(access_token=token, user=UserResponse.from_mongo(user))