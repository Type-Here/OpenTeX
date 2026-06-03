# OpenTeX

OpenTeX is a self-hosted collaborative LaTeX environment for a NoSQL database course project. The focus is on the MongoDB data model, validation, queries, and benchmarks.

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

## Seed dati

Genera dati sintetici nelle 5 collezioni MongoDB (utenti, progetti, file, permessi, log).

```bash
pip install -r seed/requirements.txt
python seed/seed.py --users 50 --projects 100 --logs 30000 --drop
```

Per i dettagli sugli argomenti e l'output atteso, vedi [`seed/README_seed.md`](seed/README_seed.md).

## Avvio rapido (Docker)

### Prerequisiti
- Docker >= 24.0
- Docker Compose >= 2.20

### Setup

```bash
# 1. Clona il repository
git clone <url-repo>
cd opentex

# 2. Configura le variabili d'ambiente
cp .env.example .env
# Edita .env con i tuoi valori (NON committare il file .env)

# 3. Avvia i servizi
docker-compose up --build -d

# 4. Verifica
curl http://localhost:8000/health
```

### Servizi esposti

| Servizio | URL | Note |
|----------|-----|------|
| Backend API | http://localhost:8000 | FastAPI + Motor |
| Swagger UI | http://localhost:8000/docs | Documentazione interattiva |
| MongoDB | localhost:27017 | Credenziali in `.env` |

### Spegnere i servizi

```bash
docker-compose down          # ferma i container
docker-compose down -v       # ferma e rimuove i volumi (reset DB)
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

## Permessi e ruoli

OpenTeX usa un sistema di permessi basato su ruoli (RBAC minimale).

### Ruoli disponibili

| Ruolo | Lettura | Modifica | Cancellazione | Gestione permessi |
|---|---|---|---|---|
| Admin | ✅ | ✅ | ✅ | ✅ |
| Editor | ✅ | ✅ | ❌ | ❌ |
| Viewer | ✅ | ❌ | ❌ | ❌ |

L'owner del progetto è sempre Admin implicito. Solo l'owner può cancellare un progetto.

### Endpoint permessi

| Metodo | URL | Autorizzazione | Descrizione |
|---|---|---|---|
| `POST` | `/projects/{id}/permissions` | Admin | Assegna/aggiorna ruolo |
| `DELETE` | `/projects/{id}/permissions/{user_id}` | Admin | Revoca accesso |
| `GET` | `/projects/{id}/permissions` | Viewer+ | Lista collaboratori |

### Autenticazione (dev/test)

Passare l'ObjectId dell'utente nell'header `X-User-Id`:

Example:
```
X-User-Id: 507f1f77bcf86cd799439011
```

---

## Frontend — Dashboard UI (Issue #6)

React + Vite dashboard per la gestione dei progetti. Richiede Node.js >= 18.

### Avvio frontend (sviluppo)

```bash
cd frontend
npm install      # solo la prima volta
npm run dev
```

L'app sarà disponibile su **http://localhost:5173** e si connette automaticamente al backend su `http://localhost:8000` tramite il dev proxy di Vite.

> Il backend deve essere in esecuzione prima di avviare il frontend.

### Funzionalità

- **Login minimale**: selezione utente dalla lista degli utenti seedati
- **Dashboard "I miei progetti"**: lista dei progetti di cui si è owner, con sezione "Shared with me" per i progetti condivisi
- **Creazione progetto**: form modale con titolo, abstract e tag (separati da virgola)
- **Modifica progetto**: aggiornamento di titolo, abstract e tag (richiede ruolo Editor o superiore)
- **Eliminazione progetto**: solo per l'owner, con conferma
- **Gestione collaboratori**: assegnazione/revoca ruoli (Admin / Editor / Viewer) — visibile solo all'owner

### Endpoint aggiunto al backend

| Metodo | URL | Descrizione |
|--------|-----|-------------|
| `GET` | `/users/` | Lista tutti gli utenti (per il login picker) |
| `GET` | `/users/{id}` | Dettaglio di un singolo utente |

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
