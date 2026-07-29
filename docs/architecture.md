# OpenTeX — Architecture

## Overview

OpenTeX is a self-hosted collaborative LaTeX environment backed by MongoDB. The system follows a three-tier architecture:

```
┌─────────────┐        HTTP/REST        ┌─────────────────┐       Motor (async)      ┌───────────────┐
│   Frontend  │ ──────────────────────► │     Backend     │ ────────────────────────► │   MongoDB 8.0 │
│ React + Vite│ ◄────────────────────── │ FastAPI + Motor │ ◄──────────────────────── │  (Docker)     │
│  port 5173  │     JSON / PDF blob     │   port 8000     │      BSON documents       │  port 27017   │
└─────────────┘                         └─────────────────┘                           └───────────────┘
```

All three services are orchestrated via Docker Compose. The backend embeds a static [Tectonic](https://tectonic-typesetting.github.io) binary for LaTeX compilation — no separate TeX installation is required.

---

## Data model — 5 collections

### Design choices: embedding vs referencing

| Decision | Choice | Reason |
|----------|--------|--------|
| Project metadata (tags, abstract) | **Embedded** in `projects` | Small, stable, always read together with the project |
| Files, permissions, activity logs | **Referenced** via `ObjectId` | Unbounded growth; media files exceed the 16 MB document limit |
| User profiles | **Referenced** from projects / permissions | Shared across many projects; updated independently |

### Collection schemas

**`users`**
```
_id, first_name, last_name, email (unique), hashed_password,
department, is_admin, created_at, preferences{language, theme}
```

**`projects`**
```
_id, title, abstract, tags[], owner_id → users,
created_at, updated_at, status
```

**`files`**
```
_id, project_id → projects, filename, file_type (tex|bib|image|pdf),
uploaded_at, uploaded_by → users, size_bytes,
content (tex/bib only) | path (image/pdf only)
```

**`permissions`**
```
_id, user_id → users, project_id → projects,
role (Admin|Editor|Viewer), granted_at, granted_by → users
```

**`activity_logs`**
```
_id, user_id → users, project_id → projects,
action, resource, resource_id, timestamp, details
```

---

## CAP theorem stance: AP

OpenTeX runs as a single MongoDB replica (or standalone instance). The design targets:

- **A**vailability — reads and writes succeed even during transient failures.
- **P**artition Tolerance — the system continues to operate in the presence of network partitions.

**Consistency** (the C in CAP) is relaxed: MongoDB provides single-document atomicity only. There are no multi-document or cross-collection transactions. Stale reads are therefore possible in edge cases (e.g., a project document updated while a permission document for the same project is being read).

### BASE semantics

| Property | Implementation |
|----------|---------------|
| **B**asically Available | FastAPI returns responses immediately; no global locks |
| **S**oft state | Derived aggregates (e.g., collaborator counts) are computed on demand, not cached |
| **E**ventually consistent | Activity logs and permission changes propagate on next read; no write-ahead synchronisation |

---

## Indexes

Five indexes are maintained to keep query latency acceptable at scale:

| Index name | Collection | Fields | Type |
|------------|-----------|--------|------|
| `projects_text_search` | `projects` | `title`, `abstract` | Full-text |
| `projects_owner_date` | `projects` | `owner_id` + `created_at` | Compound |
| `permissions_project_id` | `permissions` | `project_id` | Single field |
| `activity_logs_project_id` | `activity_logs` | `project_id` | Single field |
| `files_project_id` | `files` | `project_id` | Single field |

The `activity_logs` index delivers the largest benefit (10.9× speedup) because the collection holds 30 000+ documents — the only one where a full COLLSCAN is meaningfully slower than IXSCAN.

### Text index in the application layer

`projects_text_search` is not only a benchmark artefact: the dashboard search field calls
`GET /projects/?q=<terms>` (optionally scoped by `owner_id` or `member_id`), which builds a
`$text` filter and sorts by `{"$meta": "textScore"}`. MongoDB allows a single text index per
collection, so this query is the reason `title` and `abstract` share one compound text index
rather than two separate ones. Matching is whole-word and stemmed — a deliberate trade-off
against substring matching, which a text index cannot serve.

---

## Aggregation pipeline (JOIN)

The `/stats/projects` endpoint runs a multi-stage pipeline that joins four collections:

```
projects
  └─$lookup──► users          (owner info, department)
  └─$lookup──► permissions    (collaborator count)
  └─$lookup──► activity_logs  (activity count)
  └─$group by department
  └─$sort by total_activity DESC
```

This is the primary demonstration of cross-collection JOIN in MongoDB. Optional `department`, `date_from`, and `date_to` filters are applied at the `$match` stage before the lookups.

---

## Authentication flow

```
Client                     Backend
  │                           │
  │  POST /auth/register       │
  │  {email, password, ...}   │
  │ ────────────────────────► │  bcrypt.hash(password) → hashed_password stored in users
  │ ◄────────────────────────  │  201 Created
  │                           │
  │  POST /auth/login          │
  │  {email, password}        │
  │ ────────────────────────► │  bcrypt.verify → JWT signed with SECRET_KEY (HS256)
  │ ◄────────────────────────  │  200 {access_token, token_type, user}
  │                           │
  │  GET /projects/  (+ Bearer token)
  │ ────────────────────────► │  JWT decoded → user_id injected as dependency
  │ ◄────────────────────────  │  200 [...]
```

Tokens expire after `JWT_EXPIRATION_MINUTES` (default 1440 min / 24 h). `hashed_password` is never returned in any response.

---

## LaTeX compilation pipeline

```
POST /projects/{id}/compile
        │
        ▼
1. Fetch all tex + bib files for the project from MongoDB
2. Write files to an isolated temp directory (tempfile.mkdtemp)
3. Acquire semaphore (max 2 parallel jobs)
4. Run: tectonic --keep-logs --outdir <tmp> <entry_point.tex>
   - timeout: 60 s (asyncio.wait_for)
   - shell escape (\write18) disabled by Tectonic default
5. On success  → read output.pdf, return as application/pdf
6. On failure  → return 422 with Tectonic log text
7. On timeout  → return 504
8. Always      → shutil.rmtree(tmp)  (cleanup)
```

Entry point selection: `main.tex` if present, otherwise the first `.tex` file alphabetically.

### Instrumentation

The pipeline is split into three phases, each timed with `time.perf_counter()` and logged
on every request:

| Phase | Steps | Field |
|-------|-------|-------|
| Database query | step 1 — `files.find({project_id, file_type: tex\|bib})` | `db_ms` |
| Filesystem write | step 2 — writing the sources into the temp directory | `io_ms` |
| LaTeX compilation | step 4 — the `tectonic` subprocess | `tex_ms` |

The work is factored into `run_compilation(db, oid)` in `app/routers/compile.py`, which
returns the PDF bytes together with the timings. The compile endpoint ignores the timings
(no custom headers are added, the response is unchanged); `GET /stats/compile-benchmark`
reuses the same function to average the phases over N runs of a fixed benchmark document.
