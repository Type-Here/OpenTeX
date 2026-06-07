"""
Auth verification tests for Issue #20.
Requires the backend running at BASE_URL and the seed data loaded.
Run with: python -m tests.test_auth_api
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@opentex.org"
ADMIN_PASSWORD = "password"
TEST_EMAIL = "test_auth_issue20@opentex.org"
TEST_PASSWORD = "testpass123"

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


def req(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict | list | None]:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            r.add_header(k, v)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, None


def main() -> None:
    print("=== Auth API tests (Issue #20) ===\n")

    # ------------------------------------------------------------------
    print("Register:")
    status, body = req("POST", "/auth/register", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "Test",
        "last_name": "Auth",
        "department": "Informatica",
    })
    # 409 is acceptable on repeated runs (user already exists from a prior run)
    check("register new user → 201 (or 409 if already exists)", status in (201, 409), f"got {status}")
    if status == 201:
        check("hashed_password not in register response", "hashed_password" not in json.dumps(body or {}))

    status, _ = req("POST", "/auth/register", {
        "email": TEST_EMAIL, "password": "x",
        "first_name": "A", "last_name": "B", "department": "X",
    })
    check("duplicate email → 409", status == 409, f"got {status}")

    # ------------------------------------------------------------------
    print("\nLogin:")
    status, body = req("POST", "/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    check("admin login → 200", status == 200, f"got {status}")
    admin_token = (body or {}).get("access_token")
    check("login response contains access_token", bool(admin_token))
    check("hashed_password not in login response", "hashed_password" not in json.dumps(body or {}))

    status, body = req("POST", "/auth/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
    check("regular user login → 200", status == 200, f"got {status}")
    user_token = (body or {}).get("access_token")
    check("login response contains access_token", bool(user_token))

    status, _ = req("POST", "/auth/login", {"email": ADMIN_EMAIL, "password": "wrongpassword"})
    check("wrong password → 401", status == 401, f"got {status}")

    status, _ = req("POST", "/auth/login", {"email": "nobody@opentex.org", "password": "x"})
    check("unknown email → 401", status == 401, f"got {status}")

    # ------------------------------------------------------------------
    print("\nProtected endpoints:")

    # A valid-format ObjectId that does not exist in the DB
    FAKE_ID = "000000000000000000000099"

    status, _ = req("GET", f"/projects/{FAKE_ID}")
    check("no Authorization header → 422", status == 422, f"got {status}")

    status, _ = req("GET", f"/projects/{FAKE_ID}",
                    headers={"Authorization": "Bearer thisisnotavalidtoken"})
    check("malformed token → 401", status == 401, f"got {status}")

    if user_token:
        status, _ = req("GET", f"/projects/{FAKE_ID}",
                        headers={"Authorization": f"Bearer {user_token}"})
        check("valid token + non-existent project → 404 (auth passed)", status == 404, f"got {status}")

    # ------------------------------------------------------------------
    print("\nAdmin guard:")

    if user_token:
        status, _ = req("GET", "/stats/projects",
                        headers={"Authorization": f"Bearer {user_token}"})
        check("non-admin token on admin endpoint → 403", status == 403, f"got {status}")

    if admin_token:
        status, _ = req("GET", "/stats/projects",
                        headers={"Authorization": f"Bearer {admin_token}"})
        check("admin token on admin endpoint → 200", status == 200, f"got {status}")

    # ------------------------------------------------------------------
    print(f"\n{'=' * 40}")
    if _failures:
        print(f"FAILED: {len(_failures)} test(s): {', '.join(_failures)}")
        sys.exit(1)
    else:
        print("All tests passed.")


if __name__ == "__main__":
    main()