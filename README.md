# OpenTeX

OpenTeX is a self-hosted collaborative LaTeX environment for a NoSQL database course project. The focus is on the MongoDB data model, validation, queries, and benchmarks.

## Quick Start

**Prerequisites:** Docker >= 24.0, Docker Compose >= 2.20

```bash
# 1. Clone and configure
git clone <url-repo> && cd opentex
cp .env.example .env          # edit SECRET_KEY, MONGO_ROOT_USER, MONGO_ROOT_PASSWORD

# 2. Start all services
docker compose up -d --build

# 3. Apply schema validation
docker compose exec backend python -m scripts.validation.apply_schema_validation

# 4. (Optional) Load seed data
pip install -r seed/requirements.txt
python seed/seed.py --users 50 --projects 100 --logs 30000 --drop

# 5. Open the app
#    Frontend:  http://localhost:5173
#    API docs:  http://localhost:8000/docs
#    Seed login: admin@opentex.org / admin1234
```

> For detailed setup, environment variables, and service ports see the sections below.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture, data model, CAP/BASE notes, auth and compilation flows |
| [db/schema.md](db/schema.md) | MongoDB collection schemas and validation rules |

---

## Folder structure

- `db/` - Database documentation artifacts (schema and validation notes).
- `scripts/` - Runnable scripts for database setup and verification.
- `tests/` - Verification scripts intended for CI execution.
- `internal_docs/` - Exam-facing design notes and project workflow guidance.

## Schema and DB setup

Schema documentation lives in `db/schema.md`.

### Start MongoDB (local testing)

A full Docker Compose setup is provided in issue #3. For running the schema scripts in isolation, a single container is sufficient:

```bash
docker run -d --name opentex-mongo -p 27017:27017 mongo:8.0
```

### Apply schema validation

This script creates collections (if missing) and applies MongoDB `$jsonSchema` validators.

```bash
python -m scripts.validation.apply_schema_validation
```

Environment variables (see `.env.example`):

- `MONGODB_URI` (default: `mongodb://localhost:27017`)
- `OPENTEX_DB_NAME` (default: `opentex`)

### Verify validation (valid insert accepted, invalid rejected)

```bash
python -m tests.verify_schema_validation
```

The script inserts one valid and one invalid document per collection, prints the result, and removes all inserted test documents.

## Seed data

Generates synthetic data across the 5 MongoDB collections (users, projects, files, permissions, logs).

```bash
pip install -r seed/requirements.txt
python seed/seed.py --users 50 --projects 100 --logs 30000 --drop
```

For argument details and expected output see [`seed/README_seed.md`](seed/README_seed.md).

## Quick start (Docker)

### Prerequisites
- Docker >= 24.0
- Docker Compose >= 2.20

### Setup

```bash
# 1. Clone the repository
git clone <url-repo>
cd opentex

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your values (never commit the .env file)

# 3. Start all services
docker compose up --build -d

# 4. Verify
curl http://localhost:8000/health
```

### Exposed services

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:5173 | React + Vite |
| Backend API | http://localhost:8000 | FastAPI + Motor |
| Swagger UI | http://localhost:8000/docs | Interactive API docs |
| MongoDB | localhost:27017 | Credentials in `.env` |

### Stop services

```bash
docker compose down       # stop containers
docker compose down -v    # stop and remove volumes (DB reset)
```

---

## Benchmark — queries with vs without indexes (Issue #9)

Measures average query execution time over 10 runs, comparing the same query with and without the indexes created in issue #8.

```bash
MONGODB_URI=... OPENTEX_DB_NAME=opentex_db python -m scripts.benchmark.run_benchmark
```

The script prints a results table and a ready-to-paste markdown table at the end of its output.

### Results

Benchmark results (average over 10 runs):
```
Connected — N_RUNS=10

=== Benchmark ===
  running: Text search (title + abstract) ... 1.753 ms / 2.003 ms  (1.1x)
  running: Compound: owner_id filter + created_at sort ... 1.492 ms / 1.655 ms  (1.1x)
  running: Permissions by project_id ... 1.561 ms / 1.667 ms  (1.1x)
  running: Activity logs by project_id ... 1.750 ms / 19.024 ms  (10.9x)
  running: Files by project_id ... 1.609 ms / 1.979 ms  (1.2x)
```
| Query | With index (ms) | Without index (ms) | Speedup |
|-------|-----------------|-------------------|---------|
| Text search (title + abstract) | 1.753 | 2.003 | 1.1x |
| Compound: owner_id filter + created_at sort | 1.492 | 1.655 | 1.1x |
| Permissions by project_id | 1.561 | 1.667 | 1.1x |
| Activity logs by project_id | 1.750 | 19.024 | 10.9x |
| Files by project_id | 1.609 | 1.979 | 1.2x |

_N = 10 runs per query, averaged. 1 warmup run excluded. Text "without index" uses case-insensitive regex (equivalent semantic, forces COLLSCAN)._

**Interpretation:** The activity logs query shows the largest speedup (10.9x) because it is the only query operating on a genuinely large collection (30 000 documents). Without the index, MongoDB performs a full COLLSCAN across all 30k log entries; with the index it resolves the same query in O(log n). The remaining queries show modest gains (~1.1–1.2x) because their target collections are small (≤ 356 documents): at that scale COLLSCAN and IXSCAN complete in similar wall-clock time, and the overhead of the Docker network round-trip dominates. The speedup from these indexes would grow proportionally with data volume — at 1M activity logs the gap would widen further, as expected from the O(n) vs O(log n) complexity difference.

### Benchmark — compilation phases

Measures where time is actually spent during a LaTeX compilation, splitting
`POST /projects/{id}/compile` into three phases timed with `time.perf_counter()`:

| Phase | What it measures |
|-------|------------------|
| `db_ms` | fetching the `tex`/`bib` source documents from MongoDB |
| `io_ms` | writing those sources into the isolated temp directory |
| `tex_ms` | the `tectonic` subprocess execution |

The three timings are logged on every compile request. They are also exposed as an
admin-only endpoint that averages them over several runs:

```
GET /stats/compile-benchmark?runs=5     # runs: 1–10, default 5
```

To keep results comparable, the benchmark always compiles the **same fixed document**:
`seed/fixtures/benchmark.tex`, inserted by the seed script as `main.tex` of the
admin-owned project **"Compilation Benchmark"**. Editing the fixture invalidates
comparisons with previously recorded results. If the project is missing, the endpoint
returns 422 asking you to run the seed script.

One warm-up compilation is always run and excluded from the averages, because Tectonic
downloads and caches LaTeX packages on first use.

**From the UI:** log in as `admin@opentex.org`, open the *Benchmarks* page and use the
**Run Compilation Benchmark** button in the *Benchmark — Compilation phases* section.
It performs real compilations, so it takes roughly 30–60 s.

**Expected result:** the database phase lands in the low milliseconds while Tectonic takes
seconds, so MongoDB accounts for a fraction of a percent of the total. That is the honest
finding: the bottleneck of the compilation pipeline is the external LaTeX compiler, not the
data layer.

## Indexes (Issue #8)

Creates and verifies all indexes via a versioned script. Must be run after the schema validation script and seed data load.

| Index | Collection | Fields | Type |
|-------|-----------|--------|------|
| `projects_text_search` | `projects` | `title`, `abstract` | Text |
| `projects_owner_date` | `projects` | `owner_id` + `created_at` | Compound |
| `permissions_project_id` | `permissions` | `project_id` | Single field |
| `activity_logs_project_id` | `activity_logs` | `project_id` | Single field |
| `files_project_id` | `files` | `project_id` | Single field |

```bash
python -m scripts.indexes.create_indexes
```

The script creates all indexes and verifies usage with `explain()`, printing `[IXSCAN]` or `[COLLSCAN]` for each representative query.

## Aggregation statistics (Issue #7)

Cross-collection aggregation pipeline joining `projects → users → permissions → activity_logs`.
Returns collaboration and activity statistics grouped by owner department, sorted by total activity descending.

### Endpoint

```
GET /stats/projects
```

Optional query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `department` | string | Filter by owner department |
| `date_from` | ISO 8601 datetime | Include only projects created from this date |
| `date_to` | ISO 8601 datetime | Include only projects created up to this date |

### Example calls

```bash
# All departments
curl http://localhost:8000/stats/projects | python3 -m json.tool

# Filter by department
curl "http://localhost:8000/stats/projects?department=Engineering" | python3 -m json.tool

# Filter by date range
curl "http://localhost:8000/stats/projects?date_from=2024-01-01T00:00:00&date_to=2025-01-01T00:00:00" | python3 -m json.tool
```

### Example response

```json
[
  {
    "department": "Engineering",
    "project_count": 12,
    "total_collaborators": 34,
    "avg_collaborators": 2.83,
    "total_activity": 1520
  }
]
```

## API endpoints — Projects (Issue #4)

Base URL: `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/projects/` | Create a new project |
| `GET` | `/projects/` | List all projects (optional `?owner_id=`) |
| `GET` | `/projects/{id}` | Get a single project by ID |
| `PUT` | `/projects/{id}` | Update title / abstract / tags |
| `DELETE` | `/projects/{id}` | Delete a project |
| `GET` | `/projects/{id}/files` | List files linked to a project |

Interactive documentation: `http://localhost:8000/docs`

---

## Permissions and roles (Issue #5)

OpenTeX uses a minimal role-based access control system (RBAC).

### Available roles

| Role | Read | Edit | Delete | Manage permissions |
|------|------|------|--------|--------------------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| Editor | ✅ | ✅ | ❌ | ❌ |
| Viewer | ✅ | ❌ | ❌ | ❌ |

The project owner is always an implicit Admin. Only the owner can delete a project.

### Permission endpoints

| Method | URL | Authorization | Description |
|--------|-----|---------------|-------------|
| `POST` | `/projects/{id}/permissions` | Admin | Assign or update a role |
| `DELETE` | `/projects/{id}/permissions/{user_id}` | Admin | Revoke access |
| `GET` | `/projects/{id}/permissions` | Viewer+ | List collaborators |

All protected endpoints require a JWT in the `Authorization` header:

```
Authorization: Bearer <token>
```

Obtain a token via `POST /auth/login` (see Authentication section).

---

## Authentication (Issue #20)

Username/password login with bcrypt-hashed passwords and JWT session tokens.

### Environment variables

Add to `.env` (see `.env.example`):

```
SECRET_KEY=<long-random-string>   # used to sign JWTs — never commit this
JWT_ALGORITHM=HS256               # default, can be omitted
JWT_EXPIRATION_MINUTES=1440       # 24 h default, can be omitted
```

### Auth endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create account — body: `{email, password, first_name, last_name, department}` |
| `POST` | `/auth/login` | Get JWT — body: `{email, password}` — returns `{access_token, token_type, user}` |

`hashed_password` is never returned in any response.

### Seed credentials

The seed creates a fixed admin account and 50 regular accounts. All share password `password`. Sample emails are printed in `seed/seed_output.txt` after each run.

| Email | Account type |
|-------|--------------|
| `admin@opentex.org` | Site admin (`is_admin`) — sees statistics & benchmarks |
| _(see seed_output.txt)_ | Regular users |

> **Note:** "Site admin" here is the account-level `is_admin` flag, **not** the project-level `Admin` role from the [RBAC table](#available-roles). The two are independent: a site admin has no special rights inside a project they don't own, and a project `Admin` (shown as "Manager" in the UI) cannot see site statistics.

### Verify auth

```bash
python -m tests.test_auth_api
```

---

## LaTeX compilation (Issue #21)

Compiles a project's `.tex` and `.bib` sources into a PDF using [Tectonic](https://tectonic-typesetting.github.io). Tectonic is installed as a static binary in the backend Docker image — no local TeX installation required.

Shell escape (`\write18`) is disabled by default in Tectonic. Each compilation job runs in an isolated temporary directory (deleted after the request completes). At most 2 jobs run in parallel; excess requests are queued. A hard 60 s timeout is enforced per job.

### Endpoints

| Method | Path | Authorization | Description |
|--------|------|--------------|-------------|
| `POST` | `/projects/{id}/compile` | Viewer+ | Compile sources → PDF or error log |
| `PUT` | `/files/{id}` | Editor+ | Save edited file content |

### Compile response

- **Success** — `200 application/pdf`, PDF returned as binary attachment
- **Failure** — `422` with JSON body `{"error": "Compilation failed", "log": "..."}` containing the Tectonic log
- **Timeout** — `504` if compilation exceeds 60 s

### Example

```bash
# Compile a project (token required)
curl -X POST http://localhost:8000/projects/<project_id>/compile \
  -H "Authorization: Bearer <token>" \
  --output result.pdf

# Save edited file content (Editor role required)
curl -X PUT http://localhost:8000/files/<file_id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "\\documentclass{article}\\begin{document}Hello\\end{document}"}'
```

### Entry point selection

The compiler looks for `main.tex` as the entry point. If not found, it falls back to the first `.tex` file alphabetically. Only files with `file_type` of `tex` or `bib` are passed to the compiler.

---

## Frontend — Dashboard UI (Issues #6 + #20)

React + Vite dashboard. Included in Docker Compose — no separate `npm` step needed.

```bash
docker compose up --build -d
# frontend available at http://localhost:5173
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

### Features

- **Login / Register**: email + password form with toggle between sign-in and registration
- **Dashboard "My Projects"**: owned projects + "Shared with me" section
- **Create project**: modal form with title, abstract, and tags
- **Edit / Delete project**: Editor role or above; delete owner-only with confirmation
- **Collaborator management**: assign/revoke Admin / Editor / Viewer roles (owner only)

### Backend user endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/users/` | List all users |
| `GET` | `/users/{id}` | Get single user |

---

## Editor UI (Issue #22)

Multi-pane LaTeX editor built into the frontend. No extra services needed — it runs inside the same React app.

### Access

1. Log in and open a project from the dashboard.
2. Click **Open Editor** on the project detail page.

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back   Project Title               [Save]  [Compile]             │
├──────────┬──────────────────────────┬──────────────────────────────┤
│  Files   │                          │  Preview                  [↓][×]│
│ ──────── │   CodeMirror editor      ├──────────────────────────────┤
│ main.tex │   (LaTeX highlighting)   │                              │
│ refs.bib │                          │      PDF / error log         │
│          │                          │                              │
├──────────┴──────────────────────────┴──────────────────────────────┤
│  Status bar — save feedback / current file                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Features

- **File sidebar**: lists all project files. `.tex` and `.bib` files are selectable and editable; images and PDFs are shown but not interactive.
- **CodeMirror 6 editor**: LaTeX syntax highlighting, line numbers, keyboard navigation.
- **Save** (`Ctrl+S` / `Cmd+S` or the Save button): sends `PUT /files/{id}` with the current content. A status bar at the bottom confirms success or shows an error.
- **Compile**: sends `POST /projects/{id}/compile`. On success the compiled PDF opens in the preview pane (see Issue #23). On failure the Tectonic error log appears in the preview pane instead.

### Role requirements

| Action | Minimum role |
|--------|-------------|
| Open editor / list files | Viewer |
| Save file content | Editor |
| Compile project | Viewer |

---

## PDF Preview (Issue #23)

After clicking **Compile**, the result appears in a pane to the right of the editor — no page reload needed.

### Behaviour

| Compile result | Preview pane shows |
|---|---|
| Success (HTTP 200) | Rendered PDF via `<iframe>` |
| Failure (HTTP 422) | Tectonic error log in red monospace text |

- **↓ button**: downloads the PDF as `<project-name>.pdf` (correct filename, unlike the browser's native PDF viewer download arrow which saves as `unknown.pdf`).
- **× button**: closes the preview pane and clears the result.
- Re-compiling always replaces the previous result; the old blob URL is revoked to free memory.

---

## Local environment (conda/mamba)

Use the provided `environment.yml` for a consistent Python runtime suitable for FastAPI, Motor, and MongoDB tooling.

```bash
mamba env create -f environment.yml
mamba activate opentex
```

If `mamba` is not available:

```bash
conda env create -f environment.yml
conda activate opentex
```
