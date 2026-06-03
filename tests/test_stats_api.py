"""
Smoke tests for the Stats aggregation API (Issue #7).
Requires the backend running at BASE_URL and seed data loaded.
Run with: python -m tests.test_stats_api
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"

_failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        msg = f"  FAIL  {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        _failures.append(label)


def req(path: str) -> tuple[int, list | dict | None]:
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
        return exc.code, payload


REQUIRED_FIELDS = {"department", "project_count", "total_collaborators", "avg_collaborators", "total_activity"}


# ---------------------------------------------------------------------------
# GET /stats/projects — all departments, no filter
# ---------------------------------------------------------------------------
print("GET /stats/projects — all departments")
status, body = req("/stats/projects")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))
check("at least one department", isinstance(body, list) and len(body) > 0)
check("all items have required fields", isinstance(body, list) and all(
    REQUIRED_FIELDS.issubset(item.keys()) for item in body
))
check("counts are positive", isinstance(body, list) and all(
    item["project_count"] > 0 and item["total_activity"] > 0 for item in body
))
check("sorted by total_activity desc", isinstance(body, list) and len(body) < 2 or (
    isinstance(body, list) and all(
        body[i]["total_activity"] >= body[i + 1]["total_activity"]
        for i in range(len(body) - 1)
    )
))

unfiltered_total_projects = sum(item["project_count"] for item in body) if isinstance(body, list) else 0

# ---------------------------------------------------------------------------
# GET /stats/projects?department=Ingegneria — filter by department
# ---------------------------------------------------------------------------
print("GET /stats/projects?department=Ingegneria — filter by department")
status, body = req("/stats/projects?department=Ingegneria")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))
check("at most one entry (single department)", isinstance(body, list) and len(body) <= 1)
check("entry is Ingegneria if present", isinstance(body, list) and all(
    item["department"] == "Ingegneria" for item in body
))

# ---------------------------------------------------------------------------
# GET /stats/projects?date_from=2026-01-01T00:00:00 — recent projects only
# ---------------------------------------------------------------------------
print("GET /stats/projects?date_from=2026-01-01T00:00:00 — recent projects only")
status, body = req("/stats/projects?date_from=2026-01-01T00:00:00")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))

filtered_total_projects = sum(item["project_count"] for item in body) if isinstance(body, list) else 0
check("fewer projects than unfiltered", filtered_total_projects < unfiltered_total_projects,
      f"{filtered_total_projects} vs {unfiltered_total_projects} unfiltered")
check("all counts still positive", isinstance(body, list) and all(
    item["project_count"] > 0 for item in body
))

# ---------------------------------------------------------------------------
# GET /stats/projects?department=Informatica&date_from=2026-01-01T00:00:00 — combined filters
# ---------------------------------------------------------------------------
print("GET /stats/projects?department=Informatica&date_from=2026-01-01T00:00:00 — combined filters")
status, body = req("/stats/projects?department=Informatica&date_from=2026-01-01T00:00:00")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))
check("at most one entry", isinstance(body, list) and len(body) <= 1)

# ---------------------------------------------------------------------------
# GET /stats/projects?department=DipartimentoInesistente — unknown department → empty list
# ---------------------------------------------------------------------------
print("GET /stats/projects?department=DipartimentoInesistente — unknown department")
status, body = req("/stats/projects?department=DipartimentoInesistente")
check("status 200", status == 200, str(status))
check("returns empty list", body == [])

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"FAILED — {len(_failures)} check(s): {', '.join(_failures)}")
    sys.exit(1)
else:
    print("All checks passed.")