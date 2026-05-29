"""Shared collection names and enum values for OpenTeX."""

from typing import Final, List

# Collection names
COLLECTION_USERS: Final[str] = "users"
COLLECTION_PROJECTS: Final[str] = "projects"
COLLECTION_FILES: Final[str] = "files"
COLLECTION_PERMISSIONS: Final[str] = "permissions"
COLLECTION_ACTIVITY_LOGS: Final[str] = "activity_logs"

COLLECTION_NAMES: Final[List[str]] = [
    COLLECTION_USERS,
    COLLECTION_PROJECTS,
    COLLECTION_FILES,
    COLLECTION_PERMISSIONS,
    COLLECTION_ACTIVITY_LOGS,
]

# File types and permission roles
FILE_TYPES: Final[List[str]] = ["tex", "bib", "image", "pdf"]
PERMISSION_ROLES: Final[List[str]] = ["Admin", "Editor", "Viewer"]

# Activity actions
ACTIVITY_ACTIONS: Final[List[str]] = [
    "create_project",
    "update_project",
    "delete_project",
    "add_file",
    "update_file",
    "delete_file",
    "grant_permission",
    "revoke_permission",
]
