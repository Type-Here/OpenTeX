"""Generatore di dati sintetici per OpenTeX — 5 collezioni MongoDB."""

import argparse
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from faker import Faker
import bcrypt
from pymongo import MongoClient
from pymongo.errors import BulkWriteError, ConnectionFailure, PyMongoError

_SEED_PASSWORD_HASH = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode()

# Aggiunge il repo root a sys.path per importare il package db/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.collection_definitions import (
    ACTIVITY_ACTIONS,
    ACTIVITY_RESOURCES,
    COLLECTION_ACTIVITY_LOGS,
    COLLECTION_FILES,
    COLLECTION_NAMES,
    COLLECTION_PERMISSIONS,
    COLLECTION_PROJECTS,
    COLLECTION_USERS,
    FILE_TYPES,
    PERMISSION_ROLES,
    PROJECT_STATUSES,
)

DEPARTMENTS = [
    "Informatica",
    "Fisica",
    "Matematica",
    "Chimica",
    "Ingegneria",
    "Biologia",
]

LATEX_TAGS = [
    "latex",
    "tesi",
    "articolo",
    "beamer",
    "bibtex",
    "matematica",
    "fisica",
    "chimica",
    "nosql",
    "database",
    "ricerca",
    "machine-learning",
    "statistica",
    "relazione",
]

# Nomi file tipici per tipo
_FILE_NAMES: dict[str, list[str]] = {
    "tex": ["main.tex", "capitolo1.tex", "capitolo2.tex", "appendice.tex", "intro.tex"],
    "bib": ["bibliography.bib", "references.bib", "sources.bib"],
    "image": ["figura1.png", "schema.jpg", "grafico.svg", "diagram.eps"],
    "pdf": ["output.pdf", "bozza.pdf", "finale.pdf"],
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parsea gli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(
        description="Genera dati sintetici e li carica nelle 5 collezioni OpenTeX."
    )
    parser.add_argument("--users", type=int, default=50, help="Numero di utenti (default: 50)")
    parser.add_argument(
        "--projects", type=int, default=100, help="Numero di progetti (default: 100)"
    )
    parser.add_argument(
        "--logs", type=int, default=30000, help="Numero di activity_logs (default: 30000)"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Droppa le collezioni prima di inserire",
    )
    parser.add_argument(
        "--uri",
        type=str,
        default=None,
        help="URI MongoDB (default: MONGO_URI env o mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=os.getenv("MONGO_DB") or os.getenv("OPENTEX_DB_NAME") or "opentex_db",
        help="Nome del database (default: MONGO_DB env, poi OPENTEX_DB_NAME, poi opentex_db)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Connessione DB
# ---------------------------------------------------------------------------


def connect_db(uri: str, db_name: str):
    """Crea il client MongoDB e verifica la connessione."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client[db_name]
    except ConnectionFailure as exc:
        print(f"[ERRORE] Impossibile connettersi a MongoDB ({uri}): {exc}")
        print("Verifica che MongoDB sia avviato e che l'URI sia corretto.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Gestione collezioni
# ---------------------------------------------------------------------------


def maybe_drop_collections(db) -> None:
    """Droppa tutte le collezioni OpenTeX."""
    for name in COLLECTION_NAMES:
        db[name].drop()
        print(f"  Dropped: {name}")


def check_existing_data(db) -> None:
    """Se ci sono dati esistenti, chiede conferma interattiva prima di procedere."""
    counts = {name: db[name].count_documents({}) for name in COLLECTION_NAMES}
    if any(c > 0 for c in counts.values()):
        print("\n[AVVISO] Le collezioni contengono già dati:")
        for name, count in counts.items():
            if count > 0:
                print(f"  {name}: {count} documenti")
        answer = input("\nProcedere comunque (i nuovi record verranno aggiunti)? [y/N] ")
        if answer.strip().lower() != "y":
            print("Operazione annullata.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# Generatori
# ---------------------------------------------------------------------------


ADMIN_USER: dict = {
    "_id": ObjectId("000000000000000000000001"),
    "first_name": "Admin",
    "last_name": "OpenTeX",
    "email": "admin@opentex.org",
    "hashed_password": _SEED_PASSWORD_HASH,
    "department": "Informatica",
    "is_admin": True,
    "created_at": datetime(2024, 1, 1),
    "preferences": {"language": "en", "theme": "dark"},
}


def generate_users(n: int, fake: Faker) -> list[dict]:
    """Generate n synthetic non-admin users. All use password 'password'."""
    users = []
    for _ in range(n):
        users.append(
            {
                "_id": ObjectId(),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "hashed_password": _SEED_PASSWORD_HASH,
                "department": random.choice(DEPARTMENTS),
                "is_admin": False,
                "created_at": fake.date_time_between(start_date="-2y", end_date="-1d"),
                "preferences": {
                    "language": random.choice(["it", "en"]),
                    "theme": random.choice(["light", "dark"]),
                },
            }
        )
    return users


def generate_projects(n: int, users: list[dict], fake: Faker) -> list[dict]:
    """Genera n progetti sintetici, ognuno con un owner tra gli utenti esistenti."""
    projects = []
    for _ in range(n):
        created_at = fake.date_time_between(start_date="-1y", end_date="-1d")
        updated_at = fake.date_time_between(
            start_date=created_at, end_date=datetime.utcnow()
        )
        projects.append(
            {
                "_id": ObjectId(),
                "title": fake.sentence(nb_words=random.randint(3, 7)).rstrip("."),
                "abstract": fake.paragraph(nb_sentences=random.randint(2, 4)),
                "tags": random.sample(LATEX_TAGS, k=random.randint(1, 4)),
                "owner_id": random.choice(users)["_id"],
                "created_at": created_at,
                "updated_at": updated_at,
                "status": random.choice(PROJECT_STATUSES),
            }
        )
    return projects


def generate_permissions(
    projects: list[dict], users: list[dict], fake: Faker
) -> tuple[list[dict], dict]:
    """
    Genera i permessi per ogni progetto.

    Restituisce (permissions_list, project_permissions_map) dove
    project_permissions_map: {project_id: [user_id, ...]} con tutti gli utenti
    che hanno accesso al progetto.
    """
    permissions = []
    project_permissions_map: dict = {}

    user_ids = [u["_id"] for u in users]

    for project in projects:
        pid = project["_id"]
        owner_id = project["owner_id"]
        seen: set = {owner_id}

        # L'owner è sempre Admin
        permissions.append(
            {
                "_id": ObjectId(),
                "user_id": owner_id,
                "project_id": pid,
                "role": "Admin",
                "granted_at": project["created_at"],
                "granted_by": owner_id,
            }
        )

        # 0–3 collaboratori aggiuntivi (escluso owner)
        candidates = [uid for uid in user_ids if uid != owner_id]
        n_extra = random.randint(0, min(3, len(candidates)))
        for extra_uid in random.sample(candidates, k=n_extra):
            if extra_uid in seen:
                continue
            seen.add(extra_uid)
            permissions.append(
                {
                    "_id": ObjectId(),
                    "user_id": extra_uid,
                    "project_id": pid,
                    "role": random.choice(["Editor", "Viewer"]),
                    "granted_at": fake.date_time_between(
                        start_date=project["created_at"],
                        end_date=datetime.utcnow(),
                    ),
                    "granted_by": owner_id,
                }
            )

        project_permissions_map[pid] = list(seen)

    return permissions, project_permissions_map


def generate_files(
    projects: list[dict],
    project_permissions_map: dict,
    fake: Faker,
) -> list[dict]:
    """
    Genera 2-5 file per ogni progetto.

    Il primo file di ogni progetto è sempre un .tex (main.tex).
    uploaded_by è sempre un utente con permesso sul progetto.
    """
    files = []
    for project in projects:
        pid = project["_id"]
        authorized_users = project_permissions_map[pid]
        n_files = random.randint(2, 5)
        used_names: set[str] = set()

        for i in range(n_files):
            if i == 0:
                ftype = "tex"
                fname = "main.tex"
            else:
                ftype = random.choice(FILE_TYPES)
                candidates = _FILE_NAMES[ftype]
                fname = random.choice(candidates)
                # Evita duplicati nello stesso progetto
                suffix = 1
                base_fname = fname
                while fname in used_names:
                    stem, ext = base_fname.rsplit(".", 1)
                    fname = f"{stem}_{suffix}.{ext}"
                    suffix += 1

            used_names.add(fname)
            uploaded_at = fake.date_time_between(
                start_date=project["created_at"],
                end_date=datetime.utcnow(),
            )

            doc: dict = {
                "_id": ObjectId(),
                "project_id": pid,
                "filename": fname,
                "file_type": ftype,
                "uploaded_at": uploaded_at,
                "uploaded_by": random.choice(authorized_users),
                "size_bytes": random.randint(512, 5_242_880),
            }

            if ftype in ("tex", "bib"):
                doc["content"] = fake.paragraph(nb_sentences=random.randint(1, 3))
            else:
                doc["path"] = f"/data/projects/{pid}/{fname}"

            files.append(doc)

    return files


def generate_activity_logs(
    n: int,
    users: list[dict],
    projects: list[dict],
    files: list[dict],
    permissions: list[dict],
    project_permissions_map: dict,
    fake: Faker,
) -> list[dict]:
    """
    Genera n activity_logs distribuiti su tutti i progetti e utenti con permesso.

    resource_id punta a un documento esistente in memoria (file, permission o project).
    """
    # Indicizza per project_id
    files_by_project: dict = {}
    for f in files:
        files_by_project.setdefault(f["project_id"], []).append(f["_id"])

    perms_by_project: dict = {}
    for p in permissions:
        perms_by_project.setdefault(p["project_id"], []).append(p["_id"])

    now = datetime.utcnow()
    twelve_months_ago = now - timedelta(days=365)

    logs = []
    for _ in range(n):
        project = random.choice(projects)
        pid = project["_id"]
        user_id = random.choice(project_permissions_map[pid])
        resource = random.choice(ACTIVITY_RESOURCES)

        if resource == "file" and files_by_project.get(pid):
            resource_id = random.choice(files_by_project[pid])
        elif resource == "permission" and perms_by_project.get(pid):
            resource_id = random.choice(perms_by_project[pid])
        else:
            resource = "project"
            resource_id = pid

        action = random.choice(ACTIVITY_ACTIONS)
        timestamp = fake.date_time_between(
            start_date=twelve_months_ago, end_date=now
        )

        logs.append(
            {
                "_id": ObjectId(),
                "user_id": user_id,
                "project_id": pid,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "timestamp": timestamp,
                "details": f"{action} su {resource} {resource_id}",
            }
        )

    return logs


# ---------------------------------------------------------------------------
# Inserimento
# ---------------------------------------------------------------------------


def insert_batch(collection, documents: list[dict], batch_size: int = 500) -> int:
    """Inserisce documenti in batch; interrompe con sys.exit(1) in caso di errore."""
    total = 0
    for i in range(0, len(documents), batch_size):
        chunk = documents[i : i + batch_size]
        try:
            result = collection.insert_many(chunk, ordered=False)
            total += len(result.inserted_ids)
        except BulkWriteError as exc:
            print(f"[ERRORE] BulkWriteError su {collection.name}: {exc.details}")
            sys.exit(1)
        except PyMongoError as exc:
            print(f"[ERRORE] PyMongoError su {collection.name}: {exc}")
            sys.exit(1)
    return total


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_summary(counts: dict, elapsed: float, sample_users: list[dict]) -> None:
    """Stampa il riepilogo su stdout e lo salva in seed_output.txt."""
    lines = [
        "=== OpenTeX Seed completato ===",
        f"{'users':<20} inseriti: {counts['users']:>6}",
        f"{'projects':<20} inseriti: {counts['projects']:>6}",
        f"{'files':<20} inseriti: {counts['files']:>6}",
        f"{'permissions':<20} inseriti: {counts['permissions']:>6}",
        f"{'activity_logs':<20} inseriti: {counts['activity_logs']:>6}",
        f"Tempo totale: {elapsed:.1f}s",
        "",
        "--- Sample credentials (password: 'password') ---",
    ]
    for u in sample_users:
        admin_tag = " [ADMIN]" if u.get("is_admin") else ""
        lines.append(f"  {u['email']}{admin_tag}")
    summary = "\n".join(lines)
    print(summary)

    output_path = Path(__file__).parent / "seed_output.txt"
    output_path.write_text(summary + "\n", encoding="utf-8")
    print(f"\nOutput salvato in: {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrazione principale del seed."""
    load_dotenv()
    args = parse_args()

    uri = (
        args.uri
        or os.getenv("MONGO_URI")
        or os.getenv("MONGODB_URI")
        or "mongodb://localhost:27017"
    )

    print(f"Connessione a MongoDB: {uri} | DB: {args.db}")
    db = connect_db(uri, args.db)

    if args.drop:
        print("Dropping collezioni...")
        maybe_drop_collections(db)
    else:
        check_existing_data(db)

    fake = Faker("it_IT")
    Faker.seed(42)
    random.seed(42)

    print(
        f"\nGenerazione dati: {args.users} utenti, "
        f"{args.projects} progetti, {args.logs} log..."
    )
    t0 = time.perf_counter()

    users = [ADMIN_USER] + generate_users(args.users, fake)
    projects = generate_projects(args.projects, users, fake)
    permissions, project_permissions_map = generate_permissions(projects, users, fake)
    files = generate_files(projects, project_permissions_map, fake)
    logs = generate_activity_logs(
        args.logs, users, projects, files, permissions, project_permissions_map, fake
    )

    print("Inserimento in corso...")
    counts = {
        "users": insert_batch(db[COLLECTION_USERS], users),
        "projects": insert_batch(db[COLLECTION_PROJECTS], projects),
        "files": insert_batch(db[COLLECTION_FILES], files),
        "permissions": insert_batch(db[COLLECTION_PERMISSIONS], permissions),
        "activity_logs": insert_batch(db[COLLECTION_ACTIVITY_LOGS], logs),
    }

    elapsed = time.perf_counter() - t0
    print()
    write_summary(counts, elapsed, sample_users=users[:5])


if __name__ == "__main__":
    main()
