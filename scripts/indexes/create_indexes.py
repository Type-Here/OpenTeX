"""
Create indexes for OpenTeX and verify their usage with explain().
Run with: python -m scripts.indexes.create_indexes
"""

import asyncio

import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from db.config import get_db_name, get_mongodb_uri

# Dummy ObjectId for explain() queries — equality on a non-existent value
# still forces the planner to choose an index path (IXSCAN with 0 results).
_DUMMY_OID = ObjectId("000000000000000000000000")

INDEXES = [
    # (collection, spec, options)
    (
        "projects",
        [("title", pymongo.TEXT), ("abstract", pymongo.TEXT)],
        {"name": "projects_text_search"},
    ),
    (
        "projects",
        [("owner_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        {"name": "projects_owner_date"},
    ),
    (
        "permissions",
        [("project_id", pymongo.ASCENDING)],
        {"name": "permissions_project_id"},
    ),
    (
        "activity_logs",
        [("project_id", pymongo.ASCENDING)],
        {"name": "activity_logs_project_id"},
    ),
    (
        "files",
        [("project_id", pymongo.ASCENDING)],
        {"name": "files_project_id"},
    ),
]

# Representative queries to verify index usage via explain().
# Each entry: (label, explain_command_body)
EXPLAIN_QUERIES = [
    (
        "Text search on projects (title + abstract)",
        {"find": "projects", "filter": {"$text": {"$search": "latex"}}},
    ),
    (
        "Compound filter: owner_id equality + sort created_at desc",
        {
            "find": "projects",
            "filter": {"owner_id": _DUMMY_OID},
            "sort": {"created_at": -1},
        },
    ),
    (
        "Permissions by project_id (JOIN key for aggregation)",
        {"find": "permissions", "filter": {"project_id": _DUMMY_OID}},
    ),
    (
        "Activity logs by project_id (JOIN key for aggregation)",
        {"find": "activity_logs", "filter": {"project_id": _DUMMY_OID}},
    ),
    (
        "Files by project_id",
        {"find": "files", "filter": {"project_id": _DUMMY_OID}},
    ),
]


def _collect_stages(plan: dict, stages: list[str]) -> None:
    """Recursively collect all stage names from a query plan node."""
    if "stage" in plan:
        stages.append(plan["stage"])
    for key in ("inputStage", "inputStages"):
        child = plan.get(key)
        if isinstance(child, dict):
            _collect_stages(child, stages)
        elif isinstance(child, list):
            for item in child:
                _collect_stages(item, stages)


async def create_all_indexes(db) -> None:
    for collection, spec, options in INDEXES:
        name = await db[collection].create_index(spec, **options)
        print(f"  created  {collection}.{name}")


async def verify_index_usage(db) -> None:
    all_ok = True
    for label, query in EXPLAIN_QUERIES:
        result = await db.command({"explain": query, "verbosity": "queryPlanner"})
        winning_plan = result.get("queryPlanner", {}).get("winningPlan", {})
        stages: list[str] = []
        _collect_stages(winning_plan, stages)
        uses_index = "IXSCAN" in stages
        tag = "IXSCAN" if uses_index else "COLLSCAN"
        print(f"  [{tag}]  {label}")
        print(f"          stages: {' → '.join(stages)}")
        if not uses_index:
            all_ok = False
    if all_ok:
        print("\n  All queries use indexes.")
    else:
        print("\n  WARNING: some queries fell back to COLLSCAN — check index definitions.")


async def main() -> None:
    load_dotenv(override=True)
    uri = get_mongodb_uri()
    db_name = get_db_name()
    print(f"URI: {uri} | DB: {db_name}")

    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    await db.command("ping")
    print("Connected\n")

    print("=== Creating indexes ===")
    await create_all_indexes(db)

    print("\n=== Verifying index usage (explain) ===")
    await verify_index_usage(db)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())