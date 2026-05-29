"""Verify MongoDB schema validators with valid and invalid inserts."""


import asyncio
from datetime import datetime

import sys
from pathlib import Path

# Ensure repo root is on sys.path for module imports when run with -m.
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure, WriteError

from db.config import get_db_name, get_mongodb_uri
from scripts.validation.apply_schema_validation import apply_validators


async def insert_expect_success(collection, document, label: str) -> str:
    """Insert a document and return a label describing acceptance."""
    try:
        await collection.insert_one(document)
        return f"{label}: accepted"
    except (OperationFailure, WriteError) as exc:
        return f"{label}: rejected ({exc.__class__.__name__})"


async def insert_expect_rejection(collection, document, label: str) -> str:
    """Insert a document and return a label describing rejection."""
    try:
        await collection.insert_one(document)
        return f"{label}: accepted (unexpected)"
    except (OperationFailure, WriteError):
        return f"{label}: rejected"


async def main() -> None:
    """Run accept/reject checks for each collection and print results."""
    mongo_uri = get_mongodb_uri()
    db_name = get_db_name()

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    await db.command("ping")
    await apply_validators(db)

    now = datetime.utcnow()
    user_id = ObjectId()
    project_id = ObjectId()

    results = []

    valid_user = {
        "_id": user_id,
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Example",
        "author_name": "A. Example",
        "department": "Computer Science",
        "created_at": now,
    }
    results.append(await insert_expect_success(db.users, valid_user, "users valid"))

    invalid_user = {
        "email": "not-an-email",
        "first_name": "",
        "created_at": now,
    }
    results.append(await insert_expect_rejection(db.users, invalid_user, "users invalid"))

    valid_project = {
        "_id": project_id,
        "title": "OpenTeX Sample",
        "abstract": "Sample abstract",
        "created_at": now,
        "owner_id": user_id,
        "tags": ["latex", "nosql"],
    }
    results.append(
        await insert_expect_success(db.projects, valid_project, "projects valid")
    )

    invalid_project = {"title": "", "owner_id": "not-objectid"}
    results.append(
        await insert_expect_rejection(db.projects, invalid_project, "projects invalid")
    )

    valid_file = {
        "project_id": project_id,
        "filename": "main.tex",
        "file_type": "tex",
        "content": "\\documentclass{article}",
        "uploaded_at": now,
    }
    results.append(await insert_expect_success(db.files, valid_file, "files valid"))

    invalid_file = {
        "project_id": project_id,
        "filename": "figure.png",
        "file_type": "image",
        "uploaded_at": now,
    }
    results.append(await insert_expect_rejection(db.files, invalid_file, "files invalid"))

    valid_permission = {
        "user_id": user_id,
        "project_id": project_id,
        "role": "Admin",
        "granted_at": now,
    }
    results.append(
        await insert_expect_success(
            db.permissions, valid_permission, "permissions valid"
        )
    )

    invalid_permission = {
        "user_id": user_id,
        "project_id": project_id,
        "role": "Owner",
    }
    results.append(
        await insert_expect_rejection(
            db.permissions, invalid_permission, "permissions invalid"
        )
    )

    valid_log = {
        "user_id": user_id,
        "project_id": project_id,
        "action": "create",
        "resource": "project",
        "resource_id": project_id,
        "timestamp": now,
        "details": "Created project OpenTeX Sample",
    }
    results.append(
        await insert_expect_success(db.activity_logs, valid_log, "activity_logs valid")
    )

    invalid_log = {
        "user_id": user_id,
        "project_id": project_id,
        "action": "unknown",
        "timestamp": "now",
    }
    results.append(
        await insert_expect_rejection(
            db.activity_logs, invalid_log, "activity_logs invalid"
        )
    )

    for line in results:
        print(line)

    await db.users.delete_many({"_id": user_id})
    await db.projects.delete_many({"_id": project_id})
    await db.files.delete_many({"project_id": project_id})
    await db.permissions.delete_many({"project_id": project_id})
    await db.activity_logs.delete_many({"project_id": project_id})

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
