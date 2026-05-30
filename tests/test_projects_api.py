"""
Smoke tests for the Projects CRUD API (Issue #4).
Requires the backend to be running at BASE_URL.
Run with: python -m tests.test_projects_api
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"
OWNER_ID = "000000000000000000000001"

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


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | None]:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
        return exc.code, payload


# ---------------------------------------------------------------------------
# POST /projects/ — create
# ---------------------------------------------------------------------------
print("POST /projects/ — create")
status, body = req("POST", "/projects/", {
    "title": "Test Project",
    "abstract": "An abstract for testing",
    "owner_id": OWNER_ID,
    "tags": ["latex", "test"],
})
check("status 201", status == 201, str(status))
check("id present", isinstance(body, dict) and "id" in body)
check("title matches", isinstance(body, dict) and body.get("title") == "Test Project")
check("tags match", isinstance(body, dict) and body.get("tags") == ["latex", "test"])
check("owner_id matches", isinstance(body, dict) and body.get("owner_id") == OWNER_ID)
check("updated_at is null on create", isinstance(body, dict) and body.get("updated_at") is None)

project_id: str = body.get("id", "") if isinstance(body, dict) else ""

# ---------------------------------------------------------------------------
# GET /projects/ — list
# ---------------------------------------------------------------------------
print("GET /projects/ — list all")
status, body = req("GET", "/projects/")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))
check("created project in list", isinstance(body, list) and any(p.get("id") == project_id for p in body))

# ---------------------------------------------------------------------------
# GET /projects/?owner_id=... — filter by owner
# ---------------------------------------------------------------------------
print("GET /projects/?owner_id= — filter by owner")
status, body = req("GET", f"/projects/?owner_id={OWNER_ID}")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))
check("all items match owner", isinstance(body, list) and all(p.get("owner_id") == OWNER_ID for p in body))

# ---------------------------------------------------------------------------
# GET /projects/{id} — get by id
# ---------------------------------------------------------------------------
print(f"GET /projects/{project_id} — get by id")
status, body = req("GET", f"/projects/{project_id}")
check("status 200", status == 200, str(status))
check("id matches", isinstance(body, dict) and body.get("id") == project_id)
check("title matches", isinstance(body, dict) and body.get("title") == "Test Project")
check("abstract matches", isinstance(body, dict) and body.get("abstract") == "An abstract for testing")

# ---------------------------------------------------------------------------
# PUT /projects/{id} — partial update
# ---------------------------------------------------------------------------
print(f"PUT /projects/{project_id} — update title and tags")
status, body = req("PUT", f"/projects/{project_id}", {
    "title": "Updated Title",
    "tags": ["updated"],
})
check("status 200", status == 200, str(status))
check("title updated", isinstance(body, dict) and body.get("title") == "Updated Title")
check("tags updated", isinstance(body, dict) and body.get("tags") == ["updated"])
check("abstract unchanged", isinstance(body, dict) and body.get("abstract") == "An abstract for testing")
check("updated_at set", isinstance(body, dict) and body.get("updated_at") is not None)

# ---------------------------------------------------------------------------
# GET /projects/{id}/files — linked files (empty but 200)
# ---------------------------------------------------------------------------
print(f"GET /projects/{project_id}/files — list linked files")
status, body = req("GET", f"/projects/{project_id}/files")
check("status 200", status == 200, str(status))
check("returns list", isinstance(body, list))

# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------
print("POST /projects/ — invalid owner_id → 422")
status, _ = req("POST", "/projects/", {
    "title": "Bad",
    "abstract": "x",
    "owner_id": "not-an-objectid",
})
check("status 422", status == 422, str(status))

print(f"PUT /projects/{project_id} — empty body → 422")
status, _ = req("PUT", f"/projects/{project_id}", {})
check("status 422", status == 422, str(status))

print("GET /projects/bad-id — malformed id → 422")
status, _ = req("GET", "/projects/bad-id")
check("status 422", status == 422, str(status))

# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------
print("GET /projects/000000000000000000000099 — not found → 404")
status, _ = req("GET", "/projects/000000000000000000000099")
check("status 404", status == 404, str(status))

print("GET /projects/000000000000000000000099/files — project not found → 404")
status, _ = req("GET", "/projects/000000000000000000000099/files")
check("status 404", status == 404, str(status))

# ---------------------------------------------------------------------------
# DELETE /projects/{id}
# ---------------------------------------------------------------------------
print(f"DELETE /projects/{project_id} — delete")
status, _ = req("DELETE", f"/projects/{project_id}")
check("status 204", status == 204, str(status))

print(f"GET /projects/{project_id} — gone after delete → 404")
status, _ = req("GET", f"/projects/{project_id}")
check("status 404", status == 404, str(status))

print("DELETE /projects/000000000000000000000099 — non-existent → 404")
status, _ = req("DELETE", "/projects/000000000000000000000099")
check("status 404", status == 404, str(status))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"FAILED — {len(_failures)} check(s): {', '.join(_failures)}")
    sys.exit(1)
else:
    print("All checks passed.")