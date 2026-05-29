## Seed — Generatore dati sintetici

### Dipendenze
```bash
pip install -r seed/requirements.txt
```

### Configurazione
Copia `.env.example` in `.env` e imposta `MONGO_URI`:
```
MONGO_URI=mongodb://localhost:27017
```

### Esecuzione (default: 50 utenti, 100 progetti, 30 000 log)
```bash
python seed/seed.py
```

### Esecuzione con parametri custom
```bash
python seed/seed.py --users 100 --projects 200 --logs 50000 --drop
```

### Argomenti disponibili
| Argomento    | Tipo  | Default                         | Descrizione                              |
|--------------|-------|---------------------------------|------------------------------------------|
| `--users`    | int   | 50                              | Numero di utenti da generare             |
| `--projects` | int   | 100                             | Numero di progetti da generare           |
| `--logs`     | int   | 30000                           | Numero di activity_logs                  |
| `--drop`     | flag  | —                               | Droppa le collezioni prima di inserire   |
| `--uri`      | str   | `MONGO_URI` env o localhost     | URI MongoDB                              |
| `--db`       | str   | `opentex`                       | Nome del database                        |

### Output atteso
Lo script stampa il conteggio dei record inseriti per collezione:
```
=== OpenTeX Seed completato ===
users                inseriti:     50
projects             inseriti:    100
files                inseriti:    347
permissions          inseriti:    213
activity_logs        inseriti:  30000
Tempo totale: 4.2s
```
Il file `seed/seed_output.txt` contiene l'output dell'ultima esecuzione.

### Note
- Se le collezioni hanno già dati e `--drop` non è specificato, lo script chiede conferma interattiva.
- Prima di eseguire il seed su un DB con i validator attivi, ri-applicare i validator aggiornati:
  ```bash
  python -m scripts.validation.apply_schema_validation
  ```
