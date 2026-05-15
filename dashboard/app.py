"""
IngatlanMonitor Dashboard
=========================
Flask alkalmazás az ingatlanok táblázatos megjelenítésére.
"""

import json
import math
import re
import sqlite3
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_from_directory
from config import DATABASE, REGIONS, AIRPORT_NAMES, IMAGES_DIR

try:
    import requests as req_lib
    from bs4 import BeautifulSoup
    SCRAPING_OK = True
except ImportError:
    SCRAPING_OK = False

# ── Geo helpers ───────────────────────────────────────────────────────────────

AIRPORTS_COORDS = {
    "AGP": (36.6749, -4.4990),
    "ALC": (38.2822, -0.5582),
    "RMU": (37.8030, -1.1253),
    "VLC": (39.4893, -0.4816),
    "BIO": (43.3011, -2.9106),
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return round(R * 2 * math.asin(math.sqrt(a)))


IKEA_STORES = [
    (40.4165, -3.7026), (40.5194, -3.6374), (40.3833, -3.6500), (40.4650, -3.5880),
    (41.3784,  2.1399), (41.4270,  2.2290), (41.5450,  2.1040), (41.5718,  2.0330),
    (39.4699, -0.3763), (37.3827, -5.9732), (43.2965, -1.9760), (43.3619, -5.8444),
    (43.3209, -8.4461), (37.9092, -4.7796), (40.6430, -3.1670), (38.0056, -1.1709),
    (28.1248,-15.4300), (28.4636,-16.2518),
]

COAST_POINTS = [
    (36.7213, -4.4216), (36.5101, -4.8826), (36.3932, -5.1672),
    (38.3452, -0.4815), (37.9786, -0.6822), (38.1010, -0.7321),
    (37.6367, -0.9979), (37.5694, -1.0021), (37.8547, -1.3342),
    (39.4561, -0.3274), (39.1701, -0.1654),
    (41.3809,  2.1228), (41.7281,  2.9320),
]


def find_nearest_airport(lat, lon):
    best, best_d = None, float("inf")
    for code, (alat, alon) in AIRPORTS_COORDS.items():
        d = haversine(lat, lon, alat, alon)
        if d < best_d:
            best_d, best = d, code
    return best, best_d


def nearest_ikea_km(lat, lon):
    return round(min(haversine(lat, lon, ilat, ilon) for ilat, ilon in IKEA_STORES))


def nearest_coast_km(lat, lon):
    return round(min(haversine(lat, lon, clat, clon) for clat, clon in COAST_POINTS))


def nearest_lidl_km(lat, lon):
    try:
        from config import DATABASE
        import json as _json
        from pathlib import Path as _Path
        cache = _Path(str(DATABASE)).parent / "lidl_stores.json"
        if not cache.exists():
            return None
        stores = _json.loads(cache.read_text(encoding="utf-8"))
        if not stores:
            return None
        return round(min(haversine(lat, lon, s[0], s[1]) for s in stores))
    except Exception:
        return None


def geocode_city_nominatim(city_name):
    q = urllib.parse.urlencode({
        "q": f"{city_name}, Spain",
        "format": "json",
        "limit": 3,
        "addressdetails": 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{q}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "IngatlanMonitor/1.0 tipcsy@gmail.com"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            results = json.loads(resp.read())
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None, None


def detect_portal(url):
    u = url.lower()
    for p in ["idealista.com", "kyero.com", "thinkspain.com", "fotocasa.es"]:
        if p in u:
            return p
    return "egyéb"


def scrape_property(url):
    """Ingatlan adatok kinyerése URL-ből. Visszaad mindent amit sikerül."""
    result = {
        "property_url": url,
        "portal": detect_portal(url),
        "city": None, "price_eur": None, "size_m2": None,
        "parking": None, "garden": None,
        "latitude": None, "longitude": None,
        "airport": None, "airport_km": None, "sea_km": None,
        "original_text": None,
        "error": None,
    }

    if not SCRAPING_OK:
        result["error"] = "requests/beautifulsoup4 nincs telepítve"
        return result

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    }

    try:
        resp = req_lib.get(url, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        soup = BeautifulSoup(resp.text, "html.parser")

        # JSON-LD structured data (legjobb forrás)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0] if data else {}
                # Ár
                price = None
                if data.get("offers"):
                    price = data["offers"].get("price")
                elif data.get("price"):
                    price = data["price"]
                if price and not result["price_eur"]:
                    try:
                        result["price_eur"] = int(float(
                            str(price).replace(",", "").replace(" ", "").replace(".", "")
                        ))
                    except Exception:
                        pass
                # Város
                if data.get("address") and not result["city"]:
                    addr = data["address"]
                    result["city"] = addr.get("addressLocality") or addr.get("addressRegion")
                # Méret
                if data.get("floorSize") and not result["size_m2"]:
                    try:
                        result["size_m2"] = int(float(data["floorSize"].get("value", 0)))
                    except Exception:
                        pass
                # Koordináták
                if data.get("geo") and not result["latitude"]:
                    try:
                        lat = float(data["geo"].get("latitude", 0))
                        lon = float(data["geo"].get("longitude", 0))
                        if lat and lon:
                            result["latitude"] = lat
                            result["longitude"] = lon
                    except Exception:
                        pass
            except Exception:
                pass

        portal = result["portal"]

        # Portal-specifikus parsing
        if portal == "idealista.com":
            if not result["price_eur"]:
                el = soup.select_one(".info-data-price strong, [itemprop='price']")
                if el:
                    m = re.search(r"[\d]+", el.get_text().replace(".", "").replace(",", ""))
                    if m:
                        try:
                            result["price_eur"] = int(m.group())
                        except Exception:
                            pass
            if not result["city"]:
                bc = soup.select_one("ul.breadcrumb li:last-child, .main-info__title-minor")
                if bc:
                    result["city"] = bc.get_text(strip=True)
            if not result["size_m2"]:
                for item in soup.select(".info-features span, .details-property-feature-one span"):
                    m = re.search(r"(\d+)\s*m²", item.get_text(strip=True))
                    if m:
                        try:
                            result["size_m2"] = int(m.group(1))
                        except Exception:
                            pass
                        break
            desc_el = soup.select_one(".comment .wordwrap, [data-testid='description-content'], .adCommentsWrapper")
            if desc_el:
                result["original_text"] = desc_el.get_text(" ", strip=True)[:3000]

        elif portal == "kyero.com":
            if not result["price_eur"]:
                el = soup.select_one(".price, [data-price], h2.price")
                if el:
                    m = re.search(r"[\d]+", el.get_text().replace(".", "").replace(",", ""))
                    if m:
                        try:
                            result["price_eur"] = int(m.group())
                        except Exception:
                            pass
            if not result["city"]:
                el = soup.select_one(".location, [itemprop='addressLocality']")
                if el:
                    result["city"] = el.get_text(strip=True)
            desc_el = soup.select_one(".property-description, .description-container, .description")
            if desc_el:
                result["original_text"] = desc_el.get_text(" ", strip=True)[:3000]

        elif portal == "thinkspain.com":
            if not result["price_eur"]:
                el = soup.select_one(".asking-price, .price-title, h2.price")
                if el:
                    m = re.search(r"[\d]+", el.get_text().replace(".", "").replace(",", ""))
                    if m:
                        try:
                            result["price_eur"] = int(m.group())
                        except Exception:
                            pass
            desc_el = soup.select_one(".property-description, .description, [itemprop='description']")
            if desc_el:
                result["original_text"] = desc_el.get_text(" ", strip=True)[:3000]

        elif portal == "fotocasa.es":
            if not result["price_eur"]:
                el = soup.select_one(".re-DetailHeader-price, [data-testid='detail-header-price']")
                if el:
                    m = re.search(r"[\d]+", el.get_text().replace(".", "").replace(",", ""))
                    if m:
                        try:
                            result["price_eur"] = int(m.group())
                        except Exception:
                            pass
            desc_el = soup.select_one(".re-DetailDescription-text, [data-testid='description-text']")
            if desc_el:
                result["original_text"] = desc_el.get_text(" ", strip=True)[:3000]

        # Fallback: meta description → leírás és ár
        if not result["original_text"]:
            meta_desc = soup.find("meta", {"name": "description"}) or soup.find("meta", property="og:description")
            if meta_desc and meta_desc.get("content"):
                result["original_text"] = meta_desc["content"][:3000]

        if not result["price_eur"]:
            desc = soup.find("meta", {"name": "description"})
            if desc:
                content = desc.get("content", "").replace(".", "").replace(",", "")
                m = re.search(r"(\d{4,8})\s*€", content)
                if m:
                    try:
                        result["price_eur"] = int(m.group(1))
                    except Exception:
                        pass

        # Fallback: title/og:title → város
        if not result["city"]:
            og = soup.find("meta", property="og:title")
            title = og["content"] if og else (soup.title.string if soup.title else "")
            if title:
                m = re.search(
                    r"\b(?:in|en)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)(?:\s*[-|,]|\s*$)",
                    title,
                )
                if m:
                    result["city"] = m.group(1).strip()

    except Exception as e:
        result["error"] = str(e)

    return result

import os
import time
app = Flask(__name__)

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")

# Cache-busting: minden Flask indításkor új verzió → böngésző letölti a friss JS/CSS-t
_STATIC_VERSION = str(int(time.time()))
app.jinja_env.globals['static_ver'] = _STATIC_VERSION

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}


def migrate_db():
    """Új oszlopok hozzáadása ha még nem léteznek."""
    conn = sqlite3.connect(str(DATABASE))
    new_columns = [
        ("image_path", "TEXT"),
        ("has_garage", "INTEGER DEFAULT 0"),
        ("original_text", "TEXT"),
        ("description_hu", "TEXT"),
        ("ikea_km", "INTEGER"),
        ("lidl_km", "INTEGER"),
    ]
    for col, col_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE properties ADD COLUMN {col} {col_type}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # már létezik
    conn.close()


def get_db():
    """SQLite kapcsolat létrehozása."""
    conn = sqlite3.connect(str(DATABASE), timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


migrate_db()


@app.route("/")
def index():
    """Dashboard főoldal."""
    return render_template("index.html", regions=REGIONS, airports=AIRPORT_NAMES)


@app.route("/api/properties", methods=["GET", "POST"])
def api_properties():
    """
    GET / form-POST: DataTables server-side processing
    JSON-POST: új ingatlan létrehozása
    """
    # JSON POST = új ingatlan létrehozása
    if request.method == "POST" and request.is_json:
        return api_create_property()

    conn = get_db()
    cursor = conn.cursor()

    # POST (DataTables) vagy GET (közvetlen hívás) egyaránt
    p = request.form if request.method == "POST" else request.args

    def get_int(key, default=0):
        try:
            return int(p.get(key, default))
        except (ValueError, TypeError):
            return default

    # DataTables paraméterek
    draw = get_int("draw", 1)
    start = get_int("start", 0)
    length = get_int("length", 25)
    search_value = p.get("search[value]", "")

    # Egyedi szűrők
    region = p.get("region", "")
    min_price = get_int("min_price", 0)
    max_price = get_int("max_price", 0)
    min_size = get_int("min_size", 0)
    min_score = get_int("min_score", 0)
    show_archived = p.get("show_archived", "0") == "1"
    favorites_only = p.get("favorites_only", "0") == "1"

    # Rendezés
    order_column_idx = get_int("order[0][column]", 0)
    order_dir = p.get("order[0][dir]", "desc")

    # Oszlop mapping (DataTables index → SQL oszlop), 0. = kép (nem rendezhető)
    columns = [
        None,
        "score", "city", "price_eur", "size_m2", "sea_km",
        "airport", "airport_km", "parking", "has_garage", "garden", "garden_m2",
        "ikea_km", "lidl_km", "legal_status", "reason", "user_notes", "property_url", "email_date", "id"
    ]
    col = columns[order_column_idx] if order_column_idx < len(columns) else None
    _numeric_cols = {"price_eur", "size_m2", "sea_km", "airport_km", "garden_m2", "ikea_km", "lidl_km", "score"}
    if col in _numeric_cols:
        order_column = f"CAST({col} AS INTEGER)"
    else:
        order_column = col if col else "score"

    # Alap WHERE feltétel
    where_clauses = []
    params = []

    if not show_archived:
        where_clauses.append("is_archived = 0")

    if favorites_only:
        where_clauses.append("is_favorite = 1")

    if region:
        where_clauses.append("region = ?")
        params.append(region)

    if min_price > 0:
        where_clauses.append("price_eur >= ?")
        params.append(min_price)

    if max_price > 0:
        where_clauses.append("price_eur <= ?")
        params.append(max_price)

    if min_size > 0:
        where_clauses.append("size_m2 >= ?")
        params.append(min_size)

    if min_score > 0:
        where_clauses.append("score >= ?")
        params.append(min_score)

    if search_value:
        where_clauses.append("(city LIKE ? OR reason LIKE ? OR user_notes LIKE ?)")
        search_pattern = f"%{search_value}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Összes rekord (szűrés nélkül)
    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_archived = 0")
    total_records = cursor.fetchone()[0]

    # Szűrt rekordok száma
    cursor.execute(f"SELECT COUNT(*) FROM properties WHERE {where_sql}", params)
    filtered_records = cursor.fetchone()[0]

    # Rendezés validálás
    if order_dir not in ("asc", "desc"):
        order_dir = "desc"

    # Adatok lekérdezése
    query = f"""
        SELECT id, email_id, email_date, portal, city, region, airport, airport_km,
               sea_km, latitude, longitude, price_eur, size_m2, parking, garden,
               score, legal_status, reason, property_url, gmail_url, maps_url,
               is_archived, is_favorite, garden_m2, user_notes, image_path,
               has_garage, description_hu, ikea_km, lidl_km
        FROM properties
        WHERE {where_sql}
        ORDER BY {order_column} {order_dir}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [length, start])
    rows = cursor.fetchall()

    # DataTables formátum
    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "email_id": row["email_id"],
            "email_date": row["email_date"],
            "portal": row["portal"],
            "city": row["city"],
            "region": row["region"],
            "airport": row["airport"],
            "airport_km": row["airport_km"],
            "sea_km": row["sea_km"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "price_eur": row["price_eur"],
            "size_m2": row["size_m2"],
            "parking": row["parking"],
            "garden": row["garden"],
            "score": row["score"],
            "legal_status": row["legal_status"],
            "reason": row["reason"],
            "property_url": row["property_url"],
            "gmail_url": row["gmail_url"],
            "maps_url": row["maps_url"],
            "is_archived": row["is_archived"],
            "is_favorite": row["is_favorite"],
            "garden_m2": row["garden_m2"],
            "user_notes": row["user_notes"],
            "image_path": row["image_path"],
            "has_garage": row["has_garage"],
            "description_hu": row["description_hu"],
            "ikea_km": row["ikea_km"],
            "lidl_km": row["lidl_km"],
        })

    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": filtered_records,
        "data": data,
    })


@app.route("/api/stats")
def api_stats():
    """Statisztikák a dashboard tetejére."""
    conn = get_db()
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_archived = 0")
    stats["total"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM properties WHERE score >= 7 AND is_archived = 0")
    stats["high_score"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM properties WHERE is_favorite = 1 AND is_archived = 0")
    stats["favorites"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT region, COUNT(*) as count
        FROM properties
        WHERE is_archived = 0
        GROUP BY region
        ORDER BY count DESC
    """)
    stats["by_region"] = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return jsonify(stats)


@app.route("/api/properties/<int:prop_id>")
def api_get_property(prop_id):
    """Egy ingatlan lekérdezése szerkesztéshez."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify(dict(row))


@app.route("/api/properties/<int:prop_id>", methods=["PUT"])
def api_update_property(prop_id):
    """Ingatlan szerkesztése (összes mező)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    allowed_fields = {
        "portal", "city", "price_eur", "size_m2", "sea_km",
        "parking", "garden", "garden_m2", "airport", "airport_km",
        "latitude", "longitude", "score", "legal_status",
        "reason", "property_url", "user_notes", "has_garage",
        "description_hu", "original_text", "ikea_km", "lidl_km",
    }
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"error": "No valid fields"}), 400

    # Region újraszámítás ha reptér változott
    if "airport" in updates:
        updates["region"] = REGIONS.get(updates["airport"] or "", "Egyéb")

    # Maps URL újraszámítás ha koordináta változott
    lat = updates.get("latitude")
    lon = updates.get("longitude")
    if lat is not None and lon is not None:
        updates["maps_url"] = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else None

    conn = get_db()
    try:
        cursor = conn.cursor()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [prop_id]

        cursor.execute(f"UPDATE properties SET {set_clause} WHERE id = ?", values)
        conn.commit()
        affected = cursor.rowcount
    except Exception as e:
        conn.rollback()
        app.logger.error(f"PUT /api/properties/{prop_id} hiba: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    if affected == 0:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"success": True})


@app.route("/api/properties/<int:prop_id>/favorite", methods=["POST"])
def api_toggle_favorite(prop_id):
    """Kedvenc státusz váltása."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_favorite FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    new_value = 0 if row["is_favorite"] else 1
    cursor.execute("UPDATE properties SET is_favorite = ? WHERE id = ?", (new_value, prop_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "is_favorite": new_value})


@app.route("/api/properties/<int:prop_id>/archive", methods=["POST"])
def api_toggle_archive(prop_id):
    """Archiválás váltása."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_archived FROM properties WHERE id = ?", (prop_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    new_value = 0 if row["is_archived"] else 1
    cursor.execute("UPDATE properties SET is_archived = ? WHERE id = ?", (new_value, prop_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "is_archived": new_value})


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """URL-ből ingatlan adatok kinyerése."""
    data = request.get_json()
    if not data or not data.get("url"):
        return jsonify({"error": "URL megadása kötelező"}), 400

    url = data["url"].strip()
    result = scrape_property(url)

    # Geo számítás koordinátákból vagy városból
    lat = result.get("latitude")
    lon = result.get("longitude")
    if lat and lon:
        airport, airport_km = find_nearest_airport(lat, lon)
        result["airport"] = airport
        result["airport_km"] = airport_km
    elif result.get("city"):
        lat, lon = geocode_city_nominatim(result["city"])
        if lat and lon:
            result["latitude"] = lat
            result["longitude"] = lon
            airport, airport_km = find_nearest_airport(lat, lon)
            result["airport"] = airport
            result["airport_km"] = airport_km

    return jsonify(result)


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """Város geocoding: koordináták + legközelebbi reptér."""
    data = request.get_json()
    city = (data or {}).get("city", "").strip()
    if not city:
        return jsonify({"error": "city megadása kötelező"}), 400

    lat, lon = geocode_city_nominatim(city)
    if not lat:
        return jsonify({"error": "Város nem található"}), 404

    airport, airport_km = find_nearest_airport(lat, lon)
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    return jsonify({
        "latitude": lat,
        "longitude": lon,
        "airport": airport,
        "airport_km": airport_km,
        "maps_url": maps_url,
    })


@app.route("/api/translate", methods=["POST"])
def api_translate():
    """Teljes szöveg fordítása DeepL API-val magyarra."""
    if not DEEPL_API_KEY:
        return jsonify({"error": "DEEPL_API_KEY nincs beállítva"}), 503

    data = request.get_json()
    text = (data or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Nincs szöveg"}), 400

    try:
        if SCRAPING_OK:
            resp = req_lib.post(
                "https://api-free.deepl.com/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                json={"text": [text], "target_lang": "HU"},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        else:
            payload = urllib.parse.urlencode({
                "auth_key": DEEPL_API_KEY,
                "text": text,
                "target_lang": "HU",
            }).encode()
            req_obj = urllib.request.Request(
                "https://api-free.deepl.com/v2/translate",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req_obj, timeout=30) as r:
                result = json.loads(r.read())
        translated = result["translations"][0]["text"]
        return jsonify({"translated": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/calc_distances", methods=["POST"])
def api_calc_distances():
    """Távolságok újraszámítása koordinátákból (reptér, tenger, IKEA, Lidl)."""
    data = request.get_json()
    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"error": "Érvénytelen koordináták"}), 400

    airport, airport_km = find_nearest_airport(lat, lon)
    sea_km = nearest_coast_km(lat, lon)
    ikea_km = nearest_ikea_km(lat, lon)
    lidl_km = nearest_lidl_km(lat, lon)

    return jsonify({
        "airport": airport,
        "airport_km": airport_km,
        "sea_km": sea_km,
        "ikea_km": ikea_km,
        "lidl_km": lidl_km,
    })


@app.route("/api/ai_describe", methods=["POST"])
def api_ai_describe():
    """AI-val generál magyar leírást és kitölti a plusz mezőket az angol szöveg alapján."""
    data = request.get_json()
    text = (data or {}).get("original_text", "").strip()
    if not text:
        return jsonify({"error": "original_text megadása kötelező"}), 400

    prompt = f"""You are a real estate assistant. Based on the English/Spanish property description below, provide a structured JSON response in Hungarian.

Property description:
{text[:3000]}

Respond ONLY with valid JSON:
{{
  "description_hu": "3-5 mondatos magyar összefoglaló a főbb jellemzőkről (méret, kert, garázs, helyszín, állapot, különleges jellemzők)",
  "garden_m2": null,
  "has_garage": false,
  "parking": "igen/nem/ismeretlen",
  "garden": "igen/nem/ismeretlen",
  "score_hint": "rövid megjegyzés a pontszámhoz (opcionális)"
}}"""

    try:
        req_data = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        text_out = result.get("response", "").strip()
        json_match = re.search(r'\{.*\}', text_out, re.DOTALL)
        if not json_match:
            return jsonify({"error": "AI nem adott vissza JSON-t"}), 502
        return jsonify(json.loads(json_match.group(0)))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


def api_create_property():
    """Új ingatlan felvétele manuálisan (JSON POST)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nincs adat"}), 400

    lat = data.get("latitude")
    lon = data.get("longitude")
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else None

    airport = data.get("airport") or ""
    region = REGIONS.get(airport, "Egyéb")
    manual_id = f"manual_{uuid.uuid4().hex[:12]}"

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO properties (
                email_id, email_date, portal, city, region, airport, airport_km,
                sea_km, latitude, longitude, price_eur, size_m2, parking, garden,
                score, legal_status, reason, property_url, gmail_url, maps_url,
                garden_m2, user_notes, has_garage, description_hu, original_text, ikea_km, lidl_km
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            manual_id,
            datetime.utcnow().isoformat(),
            data.get("portal", "egyéb"),
            data.get("city"),
            region,
            airport or None,
            data.get("airport_km"),
            data.get("sea_km"),
            lat,
            lon,
            data.get("price_eur"),
            data.get("size_m2"),
            data.get("parking"),
            data.get("garden"),
            data.get("score"),
            data.get("legal_status"),
            data.get("reason"),
            data.get("property_url"),
            None,
            maps_url,
            data.get("garden_m2"),
            data.get("user_notes"),
            1 if data.get("has_garage") else 0,
            data.get("description_hu"),
            data.get("original_text"),
            data.get("ikea_km"),
            data.get("lidl_km"),
        ))
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({"error": str(e)}), 409
    finally:
        conn.close()

    return jsonify({"success": True, "id": new_id}), 201


@app.route("/api/properties/<int:prop_id>/image", methods=["POST"])
def api_upload_image(prop_id):
    """Kép feltöltése egy ingatlanhoz."""
    if "image" not in request.files:
        return jsonify({"error": "Nincs kép a kérésben"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Üres fájlnév"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"error": f"Nem engedélyezett formátum: {ext}"}), 400

    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{prop_id}_{uuid.uuid4().hex[:8]}.{ext}"
        file.save(str(IMAGES_DIR / filename))
    except Exception as e:
        app.logger.error(f"Képfájl mentési hiba prop {prop_id}: {e}", exc_info=True)
        return jsonify({"error": f"Képfájl mentési hiba: {e}"}), 500

    # Régi kép törlése (ha volt)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM properties WHERE id = ?", (prop_id,))
        row = cursor.fetchone()
        if row and row["image_path"]:
            old_file = IMAGES_DIR / row["image_path"]
            if old_file.exists():
                old_file.unlink()

        cursor.execute("UPDATE properties SET image_path = ? WHERE id = ?", (filename, prop_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Kép DB frissítési hiba prop {prop_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"success": True, "image_path": filename})


@app.route("/images/<path:filename>")
def serve_image(filename):
    """Feltöltött képek kiszolgálása."""
    return send_from_directory(str(IMAGES_DIR), filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
