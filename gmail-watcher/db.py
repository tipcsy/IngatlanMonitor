"""
SQLite adatbázis modul az IngatlanMonitor-hoz.
Az ingatlanok mentése és lekérdezése a dashboard számára.
"""

import os
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

# Adatbázis elérési útja
# Docker-ben: /app/data/ingatlan.db (megosztott volume, DATA_DIR env var-ból)
# Lokálisan: ../data/ingatlan.db
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
DB_PATH = DATA_DIR / "ingatlan.db"

# SQLite séma
SCHEMA = """
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT UNIQUE,
    email_date DATETIME,
    portal TEXT,
    city TEXT,
    region TEXT,
    airport TEXT,
    airport_km INTEGER,
    sea_km INTEGER,
    latitude REAL,
    longitude REAL,
    price_eur INTEGER,
    size_m2 INTEGER,
    parking TEXT,
    garden TEXT,
    score INTEGER,
    legal_status TEXT,
    reason TEXT,
    property_url TEXT,
    gmail_url TEXT,
    maps_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_archived INTEGER DEFAULT 0,
    is_favorite INTEGER DEFAULT 0,
    garden_m2 INTEGER,
    user_notes TEXT,
    has_garage INTEGER DEFAULT 0,
    original_text TEXT,
    description_hu TEXT,
    ikea_km INTEGER,
    lidl_km INTEGER
);

CREATE INDEX IF NOT EXISTS idx_score ON properties(score);
CREATE INDEX IF NOT EXISTS idx_airport ON properties(airport);
CREATE INDEX IF NOT EXISTS idx_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_is_archived ON properties(is_archived);
CREATE INDEX IF NOT EXISTS idx_email_date ON properties(email_date);
"""

# Reptér → régió mapping
AIRPORT_REGION = {
    "AGP": "Costa del Sol",
    "ALC": "Costa Blanca",
    "RMU": "Costa Cálida",
    "VLC": "Valencia",
    "BIO": "País Vasco",
}


def get_db_connection():
    """SQLite kapcsolat létrehozása."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Adatbázis inicializálása (táblák létrehozása ha nem léteznek)."""
    conn = get_db_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    log.info(f"[DB] Adatbázis inicializálva: {DB_PATH}")


def save_property(email_id, email_date, portal, prop, property_url, gmail_url,
                  original_text=None):
    """
    Ingatlan mentése az adatbázisba.

    Args:
        email_id: Gmail message ID (deduplikációhoz)
        email_date: Email dátuma string formátumban
        portal: Portál neve (idealista, kyero, stb.)
        prop: AI értékelés dict (city, price_eur, score, stb.)
        property_url: Ingatlan URL
        gmail_url: Gmail link az emailhez
        original_text: Eredeti e-mail szöveg (angol/spanyol)

    Returns:
        int: Beszúrt sor ID-ja, vagy None ha már létezett
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Koordináták
    coords = prop.get("coords")
    lat = coords[0] if coords else None
    lon = coords[1] if coords else None

    # Maps URL generálás
    maps_url = None
    if lat and lon:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    # Régió meghatározása reptér alapján
    airport = prop.get("airport")
    region = AIRPORT_REGION.get(airport, "Egyéb")

    # Email dátum parse
    parsed_date = None
    if email_date:
        try:
            from email.utils import parsedate_to_datetime
            parsed_date = parsedate_to_datetime(email_date).isoformat()
        except Exception:
            parsed_date = email_date

    try:
        cursor.execute("""
            INSERT INTO properties (
                email_id, email_date, portal, city, region, airport, airport_km,
                sea_km, latitude, longitude, price_eur, size_m2, parking, garden,
                score, legal_status, reason, property_url, gmail_url, maps_url,
                garden_m2, has_garage, original_text, description_hu, ikea_km, lidl_km
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email_id,
            parsed_date,
            portal,
            prop.get("city"),
            region,
            airport,
            prop.get("airport_km"),
            prop.get("sea_km"),
            lat,
            lon,
            prop.get("price_eur"),
            prop.get("size_m2"),
            prop.get("parking"),
            prop.get("garden"),
            prop.get("score"),
            prop.get("legal_status"),
            prop.get("reason"),
            property_url,
            gmail_url,
            maps_url,
            prop.get("garden_m2"),
            1 if prop.get("has_garage") else 0,
            original_text,
            prop.get("description_hu"),
            prop.get("ikea_km"),
            prop.get("lidl_km"),
        ))
        conn.commit()
        row_id = cursor.lastrowid
        log.info(f"[DB] Mentve: {prop.get('city')} | {prop.get('price_eur')} EUR | {prop.get('score')}/10 (ID: {row_id})")
        return row_id
    except sqlite3.IntegrityError:
        log.info(f"[DB] Már létezik (kihagyva): {email_id[:20]}...")
        return None
    finally:
        conn.close()


def get_property(prop_id):
    """Egy ingatlan lekérdezése ID alapján."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_property(prop_id, **kwargs):
    """
    Ingatlan frissítése (garden_m2, user_notes, is_favorite, is_archived).
    """
    allowed_fields = {"garden_m2", "user_notes", "is_favorite", "is_archived", "description_hu", "has_garage"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [prop_id]

    cursor.execute(f"UPDATE properties SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def get_stats():
    """Statisztikák lekérdezése a dashboard-hoz."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}

    # Összes aktív
    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_archived = 0")
    stats["total"] = cursor.fetchone()[0]

    # 7+ pontosak
    cursor.execute("SELECT COUNT(*) FROM properties WHERE score >= 7 AND is_archived = 0")
    stats["high_score"] = cursor.fetchone()[0]

    # Kedvencek
    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_favorite = 1 AND is_archived = 0")
    stats["favorites"] = cursor.fetchone()[0]

    # Régiónként
    cursor.execute("""
        SELECT region, COUNT(*) as count
        FROM properties
        WHERE is_archived = 0
        GROUP BY region
        ORDER BY count DESC
    """)
    stats["by_region"] = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return stats
