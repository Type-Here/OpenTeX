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
