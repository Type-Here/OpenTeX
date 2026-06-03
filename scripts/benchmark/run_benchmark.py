"""
Benchmark: query execution time with vs without indexes (Issue #9).
Each query is run N_RUNS times; the average is reported.

Run with:
  MONGODB_URI=... OPENTEX_DB_NAME=... python -m scripts.benchmark.run_benchmark
"""

import asyncio
import time

import pymongo
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from db.config import get_db_name, get_mongodb_uri

N_RUNS = 10

# Mirror of the index definitions in scripts/indexes/create_indexes.py
_INDEX_DEFS: dict[str, tuple[str, list]] = {
    "projects_text_search": (
        "projects",
        [("title", pymongo.TEXT), ("abstract", pymongo.TEXT)],
    ),
    "projects_owner_date": (
        "projects",
        [("owner_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
    ),
    "permissions_project_id": (
        "permissions",
        [("project_id", pymongo.ASCENDING)],
    ),
    "activity_logs_project_id": (
        "activity_logs",
        [("project_id", pymongo.ASCENDING)],
    ),
    "files_project_id": (
        "files",
        [("project_id", pymongo.ASCENDING)],
    ),
}


async def _avg_ms(coro_fn, n: int) -> float:
    """Run coro_fn() n times, return average elapsed milliseconds."""
    total = 0.0
    for _ in range(n):
        t0 = time.perf_counter()
        await coro_fn()
        total += (time.perf_counter() - t0) * 1000
    return total / n


async def _bench_one(db, label: str, index_name: str, with_fn, without_fn) -> dict:
    """Benchmark one query: N_RUNS with index, drop, N_RUNS without, recreate."""
    collection, spec = _INDEX_DEFS[index_name]

    # one warmup run before timing (not counted)
    await with_fn()
    avg_with = await _avg_ms(with_fn, N_RUNS)

    await db[collection].drop_index(index_name)
    try:
        await without_fn()  # warmup
        avg_without = await _avg_ms(without_fn, N_RUNS)
    finally:
        # always recreate the index, even if timing fails
        await db[collection].create_index(spec, name=index_name)

    speedup = avg_without / avg_with if avg_with > 0 else 0.0
    return {
        "label": label,
        "with_ms": round(avg_with, 3),
        "without_ms": round(avg_without, 3),
        "speedup": round(speedup, 1),
    }


async def run_all(db) -> list[dict]:
    project = await db["projects"].find_one({}, {"_id": 1, "owner_id": 1})
    if project is None:
        raise RuntimeError("No data in DB — run the seed script first.")
    owner_id = project["owner_id"]
    project_id = project["_id"]

    # Each entry: (label, index_name, with_fn, without_fn)
    # Text search: $text requires the text index, so the "without" equivalent is a
    # case-insensitive regex on both title and abstract (same semantic, forces COLLSCAN).
    benchmarks = [
        (
            "Text search (title + abstract)",
            "projects_text_search",
            lambda: db["projects"].count_documents({"$text": {"$search": "latex"}}),
            lambda: db["projects"].count_documents({"$or": [
                {"title":    {"$regex": "latex", "$options": "i"}},
                {"abstract": {"$regex": "latex", "$options": "i"}},
            ]}),
        ),
        (
            "Compound: owner_id filter + created_at sort",
            "projects_owner_date",
            lambda: db["projects"].count_documents({"owner_id": owner_id}),
            lambda: db["projects"].count_documents({"owner_id": owner_id}),
        ),
        (
            "Permissions by project_id",
            "permissions_project_id",
            lambda: db["permissions"].count_documents({"project_id": project_id}),
            lambda: db["permissions"].count_documents({"project_id": project_id}),
        ),
        (
            "Activity logs by project_id",
            "activity_logs_project_id",
            lambda: db["activity_logs"].count_documents({"project_id": project_id}),
            lambda: db["activity_logs"].count_documents({"project_id": project_id}),
        ),
        (
            "Files by project_id",
            "files_project_id",
            lambda: db["files"].count_documents({"project_id": project_id}),
            lambda: db["files"].count_documents({"project_id": project_id}),
        ),
    ]

    results = []
    for args in benchmarks:
        label = args[0]
        print(f"  running: {label} ...", end=" ", flush=True)
        result = await _bench_one(db, *args)
        results.append(result)
        print(f"{result['with_ms']:.3f} ms / {result['without_ms']:.3f} ms  ({result['speedup']}x)")

    return results


def _print_table(results: list[dict]) -> None:
    w = 44
    header = f"{'Query':<{w}} | {'With idx (ms)':>13} | {'No idx (ms)':>11} | {'Speedup':>8}"
    sep = "-" * len(header)
    print()
    print(header)
    print(sep)
    for r in results:
        print(f"{r['label']:<{w}} | {r['with_ms']:>13.3f} | {r['without_ms']:>11.3f} | {r['speedup']:>7.1f}x")
    print()
    print(f"N = {N_RUNS} runs per query, averaged. 1 warmup run excluded.")
    print("Text 'no index': regex on title+abstract (equivalent semantic, forces COLLSCAN).")


def _markdown_table(results: list[dict]) -> str:
    """Return a README-ready markdown table."""
    lines = [
        "| Query | With index (ms) | Without index (ms) | Speedup |",
        "|-------|-----------------|-------------------|---------|",
    ]
    for r in results:
        lines.append(
            f"| {r['label']} | {r['with_ms']:.3f} | {r['without_ms']:.3f} | {r['speedup']}x |"
        )
    lines.append(f"\n_N = {N_RUNS} runs per query, averaged. "
                 "Text 'without index' uses case-insensitive regex (equivalent semantic)._")
    return "\n".join(lines)


async def main() -> None:
    load_dotenv(override=True)
    uri = get_mongodb_uri()
    db_name = get_db_name()
    print(f"URI: {uri} | DB: {db_name}")

    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    await db.command("ping")
    print(f"Connected — N_RUNS={N_RUNS}\n")

    print("=== Benchmark ===")
    results = await run_all(db)

    print("\n=== Results table ===")
    _print_table(results)

    print("\n=== Markdown (copy into README) ===")
    print(_markdown_table(results))

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
