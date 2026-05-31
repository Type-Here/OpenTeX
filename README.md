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
