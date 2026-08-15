"""
MariaDB adatbázis modul az IngatlanMonitor-hoz.
Az ingatlanok mentése és lekérdezése a dashboard számára.
"""

import os
import logging
import pymysql
import pymysql.cursors
from pathlib import Path
from datetime import datetime

# Ez az import tölti be a .env-et. Minden más elé kell, mert az alábbi
# konstansok már import-időben olvassák a környezeti változókat.
from envfile import require, optional

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))

DB_HOST = optional("DB_HOST", "localhost")
DB_PORT = int(optional("DB_PORT", "3306"))
DB_USER = optional("DB_USER", "ingatlan")
DB_PASSWORD = require("DB_PASSWORD", "a MariaDB jelszava")
DB_NAME = optional("DB_NAME", "ingatlan")

AIRPORT_REGION = {
    "AGP": "Costa del Sol",
    "ALC": "Costa Blanca",
    "RMU": "Costa Cálida",
    "VLC": "Valencia",
    "BIO": "País Vasco",
    "BRU": "Brüsszel környéke",
    "CRL": "Brüsszel környéke",
}


def get_db_connection():
    """MariaDB kapcsolat létrehozása."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        autocommit=False,
    )


def init_db():
    """Tábla létrehozása ha nem létezik."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email_id VARCHAR(255) UNIQUE,
            email_date DATETIME,
            portal VARCHAR(50),
            city VARCHAR(255),
            region VARCHAR(100),
            airport VARCHAR(10),
            airport_km INT,
            sea_km INT,
            latitude DOUBLE,
            longitude DOUBLE,
            price_eur INT,
            size_m2 INT,
            parking VARCHAR(20),
            garden VARCHAR(20),
            score INT,
            legal_status VARCHAR(20),
            reason TEXT,
            property_url TEXT,
            gmail_url TEXT,
            maps_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_archived INT DEFAULT 0,
            is_favorite INT DEFAULT 0,
            garden_m2 INT,
            user_notes TEXT,
            image_path TEXT,
            has_garage INT DEFAULT 0,
            original_text MEDIUMTEXT,
            description_hu MEDIUMTEXT,
            ikea_km INT,
            lidl_km INT,
            country VARCHAR(2) DEFAULT 'ES',
            rooms INT,
            bathrooms INT,
            capital_km INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # Meglévő (már élő) táblák bővítése, ha korábbi verzióból frissítünk
    for ddl in (
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS country VARCHAR(2) DEFAULT 'ES'",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS rooms INT",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS bathrooms INT",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS capital_km INT",
    ):
        cursor.execute(ddl)
    conn.commit()
    conn.close()
    log.info(f"[DB] MariaDB inicializálva: {DB_HOST}/{DB_NAME}")


def save_property(email_id, email_date, portal, prop, property_url, gmail_url,
                  original_text=None):
    """
    Ingatlan mentése az adatbázisba.

    Returns:
        int: Beszúrt sor ID-ja, vagy None ha már létezett
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    coords = prop.get("coords")
    lat = coords[0] if coords else None
    lon = coords[1] if coords else None

    maps_url = None
    if lat and lon:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    airport = prop.get("airport")
    region = AIRPORT_REGION.get(airport, "Egyéb")

    parsed_date = None
    if email_date:
        try:
            from email.utils import parsedate_to_datetime
            from datetime import timezone as _tz
            parsed_date = parsedate_to_datetime(email_date).astimezone(_tz.utc).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            parsed_date = None

    try:
        cursor.execute("""
            INSERT INTO properties (
                email_id, email_date, portal, city, region, airport, airport_km,
                sea_km, latitude, longitude, price_eur, size_m2, parking, garden,
                score, legal_status, reason, property_url, gmail_url, maps_url,
                garden_m2, has_garage, original_text, description_hu, ikea_km, lidl_km,
                country, rooms, bathrooms, capital_km
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            prop.get("country", "ES"),
            prop.get("rooms"),
            prop.get("bathrooms"),
            prop.get("capital_km"),
        ))
        conn.commit()
        row_id = cursor.lastrowid
        log.info(f"[DB] Mentve: {prop.get('city')} | {prop.get('price_eur')} EUR | {prop.get('score')}/10 (ID: {row_id})")
        return row_id
    except pymysql.err.IntegrityError:
        log.info(f"[DB] Már létezik (kihagyva): {email_id[:20]}...")
        return None
    finally:
        conn.close()


def get_property(prop_id):
    """Egy ingatlan lekérdezése ID alapján."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = %s", (prop_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_property(prop_id, **kwargs):
    """Ingatlan frissítése."""
    allowed_fields = {"garden_m2", "user_notes", "is_favorite", "is_archived", "description_hu", "has_garage"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
    values = list(updates.values()) + [prop_id]

    cursor.execute(f"UPDATE properties SET {set_clause} WHERE id = %s", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def get_stats():
    """Statisztikák lekérdezése."""
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) AS cnt FROM properties WHERE is_archived = 0")
    stats["total"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM properties WHERE score >= 7 AND is_archived = 0")
    stats["high_score"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM properties WHERE is_favorite = 1 AND is_archived = 0")
    stats["favorites"] = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT region, COUNT(*) AS count
        FROM properties
        WHERE is_archived = 0
        GROUP BY region
        ORDER BY count DESC
    """)
    stats["by_region"] = {row["region"]: row["count"] for row in cursor.fetchall()}

    conn.close()
    return stats
