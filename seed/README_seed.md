## Seed — Synthetic data generator

### Dependencies
```bash
pip install -r seed/requirements.txt
```

### Configuration
Copy `.env.example` to `.env` and set `MONGO_URI`:
```
MONGO_URI=mongodb://localhost:27017
```

### Run with defaults (50 users, 100 projects, 30 000 logs)
```bash
python seed/seed.py
```

### Run with custom parameters
```bash
python seed/seed.py --users 100 --projects 200 --logs 50000 --drop
```

### Available arguments
| Argument     | Type  | Default                         | Description                                      |
|--------------|-------|---------------------------------|--------------------------------------------------|
| `--users`    | int   | 50                              | Number of users to generate                      |
| `--projects` | int   | 100                             | Number of projects to generate                   |
| `--logs`     | int   | 30000                           | Number of activity_logs                          |
| `--drop`     | flag  | —                               | Drop collections before inserting                |
| `--uri`      | str   | `MONGO_URI` env or localhost    | MongoDB URI                                      |
| `--db`       | str   | `opentex`                       | Database name                                    |

### Expected output
The script prints the inserted record count per collection:
```
=== OpenTeX Seed completed ===
users                inserted:     50
projects             inserted:    100
files                inserted:    347
permissions          inserted:    213
activity_logs        inserted:  30000
Total time: 4.2s
```
The file `seed/seed_output.txt` contains the output of the last run.

### Notes
- If collections already contain data and `--drop` is not specified, the script asks for interactive confirmation.
- Before running the seed on a DB with active validators, re-apply the updated validators:
  ```bash
  python -m scripts.validation.apply_schema_validation
  ```
