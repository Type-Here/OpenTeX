"""MongoDB $jsonSchema validators for OpenTeX collections."""

from typing import Any, Dict

from db.collection_definitions import (
    ACTIVITY_ACTIONS,
    COLLECTION_ACTIVITY_LOGS,
    COLLECTION_FILES,
    COLLECTION_PERMISSIONS,
    COLLECTION_PROJECTS,
    COLLECTION_USERS,
    FILE_TYPES,
    PERMISSION_ROLES,
)


def get_validators() -> Dict[str, Dict[str, Any]]:
    """Return per-collection validators used by setup and tests."""
    return {
        COLLECTION_USERS: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "email",
                    "first_name",
                    "last_name",
                    "department",
                    "created_at",
                ],
                "properties": {
                    "email": {
                        "bsonType": "string",
                        "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$",
                    },
                    "first_name": {"bsonType": "string", "minLength": 1},
                    "last_name": {"bsonType": "string", "minLength": 1},
                    "author_name": {"bsonType": "string"},
                    "department": {"bsonType": "string", "minLength": 1},
                    "created_at": {"bsonType": "date"},
                    "preferences": {"bsonType": "object"},
                    "orcid": {"bsonType": "string"},
                },
            }
        },
        COLLECTION_PROJECTS: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["title", "abstract", "created_at", "owner_id"],
                "properties": {
                    "title": {"bsonType": "string", "minLength": 1},
                    "abstract": {"bsonType": "string", "minLength": 1},
                    "tags": {
                        "bsonType": "array",
                        "items": {"bsonType": "string"},
                    },
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                    "owner_id": {"bsonType": "objectId"},
                },
            }
        },
        COLLECTION_FILES: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["project_id", "filename", "file_type", "created_at"],
                "properties": {
                    "project_id": {"bsonType": "objectId"},
                    "filename": {"bsonType": "string", "minLength": 1},
                    "file_type": {
                        "enum": FILE_TYPES,
                    },
                    "content": {"bsonType": "string"},
                    "path": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                },
                "oneOf": [
                    {
                        "properties": {"file_type": {"enum": ["tex", "bib"]}},
                        "required": ["content"],
                    },
                    {
                        "properties": {"file_type": {"enum": ["image", "pdf"]}},
                        "required": ["path"],
                    },
                ],
            }
        },
        COLLECTION_PERMISSIONS: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "project_id", "role", "granted_at"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "project_id": {"bsonType": "objectId"},
                    "role": {"enum": PERMISSION_ROLES},
                    "granted_at": {"bsonType": "date"},
                },
            }
        },
        COLLECTION_ACTIVITY_LOGS: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "project_id", "action", "timestamp"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "project_id": {"bsonType": "objectId"},
                    "action": {
                        "enum": ACTIVITY_ACTIONS,
                    },
                    "timestamp": {"bsonType": "date"},
                    "metadata": {"bsonType": "object"},
                },
            }
        },
    }
