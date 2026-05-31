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
