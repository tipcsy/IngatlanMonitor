#!/usr/bin/env python3
"""
SQLite → MariaDB adatmigráció
Futtatás: python migrate_sqlite_to_mariadb.py
"""

import os
import sqlite3
import pymysql
import sys
from pathlib import Path

# A gyökérben lévő .env beolvasása (nincs verziókövetve — lásd .env.example).
_env = Path(__file__).resolve().parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

SQLITE_PATH = os.environ.get("SQLITE_PATH", "") or str(
    Path(os.environ.get("DATA_DIR", "./data")) / "ingatlan.db"
)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "ingatlan")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "ingatlan")

if not DB_PASSWORD:
    sys.exit(
        "Hiányzó DB_PASSWORD. Másold le a .env.example fájlt .env néven, és töltsd ki."
    )

COLUMNS = [
    "email_id", "email_date", "portal", "city", "region", "airport", "airport_km",
    "sea_km", "latitude", "longitude", "price_eur", "size_m2", "parking", "garden",
    "score", "legal_status", "reason", "property_url", "gmail_url", "maps_url",
    "created_at", "is_archived", "is_favorite", "garden_m2", "user_notes",
    "image_path", "has_garage", "original_text", "description_hu", "ikea_km", "lidl_km",
]


def main():
    sqlite_path = Path(SQLITE_PATH)
    if not sqlite_path.exists():
        print(f"HIBA: SQLite fájl nem található: {SQLITE_PATH}", file=sys.stderr)
        sys.exit(1)

    src = sqlite3.connect(str(sqlite_path), timeout=30)
    src.row_factory = sqlite3.Row

    dst = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        charset="utf8mb4", autocommit=False,
    )

    src_cursor = src.cursor()
    dst_cursor = dst.cursor()

    # Meglévő rekordok száma a célban
    dst_cursor.execute("SELECT COUNT(*) AS cnt FROM properties")
    existing = dst_cursor.fetchone()[0]
    if existing > 0:
        print(f"FIGYELMEZTETÉS: MariaDB-ben már van {existing} rekord.")
        answer = input("Folytatod? (igen/nem): ").strip().lower()
        if answer != "igen":
            print("Megszakítva.")
            src.close()
            dst.close()
            return

    # Forrás rekordok lekérdezése
    col_select = ", ".join(COLUMNS)
    src_cursor.execute(f"SELECT {col_select} FROM properties ORDER BY id")
    rows = src_cursor.fetchall()
    print(f"Átmásolandó rekordok: {len(rows)}")

    placeholders = ", ".join(["%s"] * len(COLUMNS))
    col_list = ", ".join(COLUMNS)
    insert_sql = f"INSERT IGNORE INTO properties ({col_list}) VALUES ({placeholders})"

    ok = 0
    errors = 0
    for row in rows:
        try:
            values = [row[c] for c in COLUMNS]
            dst_cursor.execute(insert_sql, values)
            ok += 1
        except Exception as e:
            errors += 1
            print(f"  Hiba: {e}")

    dst.commit()
    print(f"Kész: {ok} rekord átmásolva, {errors} hiba.")
    src.close()
    dst.close()


if __name__ == "__main__":
    main()
