Importer for TV shows CSV -> MySQL

What this does
- Reads the CSV `10k_Poplar_Tv_Shows.csv` (same folder by default).
- Parses `genre_ids` and `origin_country` which are stored as arrays in the CSV.
- Inserts data into the normalized MySQL schema created by `create_tv_shows_db.sql`.

Files added
- `import_tv_shows.py` — the importer script (uses SQLAlchemy + pymysql + pandas).
- `requirements.txt` — Python deps.
- `create_tv_shows_db.sql` — (already present) schema creation and transform examples.

Quick start (Windows PowerShell)
1) Create the DB schema (if you haven't already):
   - Open MySQL Workbench or mysql client and run `create_tv_shows_db.sql`.

2) Install Python deps (recommend a venv):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r "c:\Users\gerbi\OneDrive\Desktop\TCU\Juinor Yr\First Semester\Database\Project\Dataset\Database Program\requirements.txt"
```

3) Run the importer (example):
```powershell
python import_tv_shows.py --csv "10k_Poplar_Tv_Shows.csv" --host localhost --user root --password MySecret --db tv_shows_db
```
    
Options
- --csv : path to CSV (default: `10k_Poplar_Tv_Shows.csv` in current folder)
- --host, --port, --user, --password, --db
- --batch : number of rows per batch (default 500)

Notes and caveats
- The script writes directly to the normalized tables and uses INSERT IGNORE / INSERT ... ON DUPLICATE KEY UPDATE.
- If your CSV contains malformed list fields, the script tries several parse strategies (json, replace single quotes, ast.literal_eval).
- The script does not populate `genres.name` or `countries.country_name` — you can add those manually or with an extra mapping.

If you'd like
- I can add an option to run `create_tv_shows_db.sql` automatically before importing.
- I can add a dry-run mode that prints sample SQL without executing it.
- I can add genre-name population from a TMDB mapping.
