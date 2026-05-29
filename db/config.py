"""Shared database configuration helpers for OpenTeX."""

import os
from typing import Final

ENV_MONGODB_URI: Final[str] = "MONGODB_URI"
ENV_DB_NAME: Final[str] = "OPENTEX_DB_NAME"
DEFAULT_MONGODB_URI: Final[str] = "mongodb://localhost:27017"
DEFAULT_DB_NAME: Final[str] = "opentex"


def get_mongodb_uri() -> str:
    """Return the MongoDB connection URI from the environment or defaults."""
    return os.getenv(ENV_MONGODB_URI, DEFAULT_MONGODB_URI)


def get_db_name() -> str:
    """Return the MongoDB database name from the environment or defaults."""
    return os.getenv(ENV_DB_NAME, DEFAULT_DB_NAME)
