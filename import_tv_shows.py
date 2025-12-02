"""
import_tv_shows.py

Reads the CSV `10k_Poplar_Tv_Shows.csv`, parses multi-valued fields (genre_ids and origin_country),
and inserts data into the normalized MySQL schema created by `create_tv_shows_db.sql`:
  - shows
  - genres
  - show_genres
  - countries
  - show_countries
  - popularity_history

Usage examples (Windows PowerShell):
  python import_tv_shows.py --csv "10k_Poplar_Tv_Shows.csv" --user root --password secret --host localhost --db tv_shows_db

Options:
  --csv        Path to CSV file (default: ./10k_Poplar_Tv_Shows.csv)
  --host       MySQL host (default: localhost)
  --port       MySQL port (default: 3306)
  --user       MySQL username (default: root)
  --password   MySQL password (default: empty)
  --db         Database name (default: tv_shows_db)
  --batch      Number of rows per batch insert (default: 500)

This script uses SQLAlchemy + pymysql for DB connections and pandas to read the CSV robustly.
"""

import argparse
import json
import ast
import math
from typing import List, Any
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def parse_list_field(value: Any) -> List:
    """Parse fields like "[10765, 9648]" or "['US']" into Python lists.
    Returns an empty list on parse failure or blank input.
    """
    if value is None:
        return []
    s = str(value).strip()
    if s == '' or s.lower() == 'nan':
        return []

    # Try JSON first (works for [1, 2] or ["US","GB"]).
    try:
        return json.loads(s)
    except Exception:
        pass

    # Replace single quotes with double quotes and try JSON again
    try:
        s2 = s.replace("'", '"')
        return json.loads(s2)
    except Exception:
        pass

    # Fall back to ast.literal_eval which can evaluate Python-literal lists
    try:
        val = ast.literal_eval(s)
        if isinstance(val, (list, tuple)):
            return list(val)
        return [val]
    except Exception:
        return []


def safe_cast_float(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        s = str(x).strip()
        if s == '':
            return None
        return float(s)
    except Exception:
        return None


def safe_cast_int(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        s = str(x).strip()
        if s == '':
            return None
        return int(float(s))
    except Exception:
        return None


def upsert_shows(conn, rows):
    """Batch upsert into shows using INSERT ... ON DUPLICATE KEY UPDATE."""
    if not rows:
        return
    sql = text("""
    INSERT INTO shows (id, adult, backdrop_path, original_name, name, overview, original_language, poster_path, first_air_date, vote_average, vote_count, popularity)
    VALUES (:id, :adult, :backdrop_path, :original_name, :name, :overview, :original_language, :poster_path, :first_air_date, :vote_average, :vote_count, :popularity)
    ON DUPLICATE KEY UPDATE
      adult = VALUES(adult),
      backdrop_path = VALUES(backdrop_path),
      original_name = VALUES(original_name),
      name = VALUES(name),
      overview = VALUES(overview),
      original_language = VALUES(original_language),
      poster_path = VALUES(poster_path),
      first_air_date = VALUES(first_air_date),
      vote_average = VALUES(vote_average),
      vote_count = VALUES(vote_count),
      popularity = VALUES(popularity)
    """)
    conn.execute(sql, rows)


def insert_ignore(conn, table, columns, rows):
    """Generic INSERT IGNORE for many rows.
    table: str, columns: list of names, rows: list of tuples or dict-compatible (we'll pass dicts as parameter lists)
    """
    if not rows:
        return
    cols = ','.join(columns)
    vals = ','.join([f":{c}" for c in columns])
    sql = text(f"INSERT IGNORE INTO {table} ({cols}) VALUES ({vals})")
    conn.execute(sql, rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='10k_Poplar_Tv_Shows.csv', help='Path to CSV file')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default=3306, type=int)
    parser.add_argument('--user', default='root')
    parser.add_argument('--password', default='')
    parser.add_argument('--db', default='tv_shows_db')
    parser.add_argument('--batch', default=500, type=int)
    args = parser.parse_args()

    csv_path = args.csv

    print(f"Reading CSV: {csv_path} (this may take a while)")
    df = pd.read_csv(csv_path)
    print(f"Rows read: {len(df)}")

    # Normalize column names if needed
    # Ensure expected columns exist
    expected = ['adult','backdrop_path','genre_ids','id','origin_country','original_language','original_name','overview','popularity','poster_path','first_air_date','name','vote_average','vote_count']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV missing expected columns: {missing}")

    # Parse list fields and compute flattened sets for genres and countries
    print("Parsing multi-valued fields (genre_ids, origin_country)...")
    df['parsed_genres'] = df['genre_ids'].apply(parse_list_field)
    df['parsed_countries'] = df['origin_country'].apply(parse_list_field)

    # DB engine
    engine_url = f"mysql+pymysql://{args.user}:{args.password}@{args.host}:{args.port}/{args.db}?charset=utf8mb4"
    print(f"Connecting to DB: {engine_url}")
    engine: Engine = create_engine(engine_url, pool_pre_ping=True)

    # Prepare batch inserts
    shows_batch = []
    genres_set = set()
    show_genres_pairs = []
    countries_set = set()
    show_countries_pairs = []
    popularity_rows = []

    for _, row in df.iterrows():
        show_id = safe_cast_int(row['id'])
        if show_id is None:
            continue
        adult_val = 1 if str(row['adult']).strip().lower() in ('true','1','yes') else 0
        backdrop = row['backdrop_path'] if pd.notna(row['backdrop_path']) and str(row['backdrop_path']).strip()!='' else None
        original_name = row['original_name'] if pd.notna(row['original_name']) and str(row['original_name']).strip()!='' else None
        name = row['name'] if pd.notna(row['name']) and str(row['name']).strip()!='' else None
        overview = row['overview'] if pd.notna(row['overview']) and str(row['overview']).strip()!='' else None
        original_language = row['original_language'] if pd.notna(row['original_language']) and str(row['original_language']).strip()!='' else None
        poster_path = row['poster_path'] if pd.notna(row['poster_path']) and str(row['poster_path']).strip()!='' else None

        # parse first_air_date to YYYY-MM-DD if possible
        first_air_date = None
        try:
            if pd.notna(row['first_air_date']) and str(row['first_air_date']).strip()!='':
                first_air_date = pd.to_datetime(row['first_air_date'], errors='coerce').date()
        except Exception:
            first_air_date = None

        vote_average = safe_cast_float(row['vote_average'])
        vote_count = safe_cast_int(row['vote_count'])
        popularity = safe_cast_float(row['popularity'])

        shows_batch.append({
            'id': show_id,
            'adult': adult_val,
            'backdrop_path': backdrop,
            'original_name': original_name,
            'name': name,
            'overview': overview,
            'original_language': original_language,
            'poster_path': poster_path,
            'first_air_date': first_air_date,
            'vote_average': vote_average,
            'vote_count': vote_count,
            'popularity': popularity
        })

        # genres
        try:
            g_list = parse_list_field(row['genre_ids'])
            for g in g_list:
                try:
                    gid = int(g)
                    genres_set.add(gid)
                    show_genres_pairs.append({'show_id': show_id, 'genre_id': gid})
                except Exception:
                    pass
        except Exception:
            pass

        # countries
        try:
            c_list = parse_list_field(row['origin_country'])
            for cc in c_list:
                if cc is None:
                    continue
                code = str(cc).strip()
                if code == '':
                    continue
                countries_set.add(code)
                show_countries_pairs.append({'show_id': show_id, 'country_code': code})
        except Exception:
            pass

        # popularity history row
        if popularity is not None or vote_average is not None or vote_count is not None:
            popularity_rows.append({
                'show_id': show_id,
                'popularity': popularity if popularity is not None else 0.0,
                'vote_average': vote_average,
                'vote_count': vote_count,
                'source': 'initial_import'
            })

    print(f"Prepared: {len(shows_batch)} shows, {len(genres_set)} unique genres, {len(countries_set)} unique countries")

    # Execute DB inserts in a transaction
    with engine.begin() as conn:
        print("Upserting shows in batches...")
        b = args.batch
        for i in range(0, len(shows_batch), b):
            upsert_shows(conn, shows_batch[i:i+b])
            print(f"  Upserted shows {i}..{min(i+b, len(shows_batch))}")

        # Insert genres
        print("Inserting genres master list...")
        genre_rows = [{'genre_id': g} for g in genres_set]
        if genre_rows:
            insert_ignore(conn, 'genres', ['genre_id'], genre_rows)

        # Insert countries
        print("Inserting countries master list (codes only)...")
        country_rows = [{'country_code': c} for c in countries_set]
        if country_rows:
            insert_ignore(conn, 'countries', ['country_code'], country_rows)

        # Insert show_genres
        print("Inserting show_genres relationships...")
        # deduplicate pairs
        seen = set()
        dedup_pairs = []
        for p in show_genres_pairs:
            key = (p['show_id'], p['genre_id'])
            if key in seen:
                continue
            seen.add(key)
            dedup_pairs.append(p)
        for i in range(0, len(dedup_pairs), b):
            insert_ignore(conn, 'show_genres', ['show_id','genre_id'], dedup_pairs[i:i+b])

        # Insert show_countries
        print("Inserting show_countries relationships...")
        seen = set()
        dedup_pairs = []
        for p in show_countries_pairs:
            key = (p['show_id'], p['country_code'])
            if key in seen:
                continue
            seen.add(key)
            dedup_pairs.append(p)
        for i in range(0, len(dedup_pairs), b):
            insert_ignore(conn, 'show_countries', ['show_id','country_code'], dedup_pairs[i:i+b])

        # Insert popularity_history
        print("Inserting popularity_history rows...")
        for i in range(0, len(popularity_rows), b):
            insert_ignore(conn, 'popularity_history', ['show_id','popularity','vote_average','vote_count','source'], popularity_rows[i:i+b])

    print("Import complete.")


if __name__ == '__main__':
    main()
