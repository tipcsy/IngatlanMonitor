"""
Gmail Ingatlan Watcher
======================
Lekérdezi a Gmail 'Hírlevelek/Ingatlan' mappát, AI-val kiértékeli
a spanyol ingatlan ajánlatokat, és Telegram értesítőt küld ha 7+ pontos.

Futtatás: python gmail_watcher.py
"""

import os
import json
import base64
import re
import pickle
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from db import init_db, save_property, DATA_DIR

# ── .env betöltése ────────────────────────────────────────────────────────────

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging():
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gmail_watcher.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = RotatingFileHandler(
        str(log_file), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

setup_logging()
log = logging.getLogger(__name__)

# ── Konfiguráció ──────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent
CLIENT_SECRET = BASE_DIR / "client_secret.json"
TOKEN_FILE    = BASE_DIR / "token.pickle"
STATE_FILE    = BASE_DIR / "state.json"
RULES_FILE    = BASE_DIR.parent / "RULES.md"

GMAIL_LABEL = "Hírlevelek/Ingatlan"

PORTALS = [
    "idealista.com",
    "kyero.com",
    "thinkspain.com",
    "fotocasa.es",
]

ALL_PORTALS = PORTALS + ["ingatlan.com", "immoweb.be", "koltozzbe.hu"]

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Ismert városok → legközelebbi reptér (fallback ha az AI nem adja meg)
CITY_AIRPORT_MAP = {
    # Costa del Sol / Málaga
    "malaga": ("AGP", 8), "málaga": ("AGP", 8), "marbella": ("AGP", 60),
    "fuengirola": ("AGP", 25), "torremolinos": ("AGP", 12), "nerja": ("AGP", 55),
    "estepona": ("AGP", 80), "benalmadena": ("AGP", 18), "mijas": ("AGP", 30),
    "chiclana": ("AGP", 145), "casares": ("AGP", 95),
    # Costa Blanca / Alicante
    "alicante": ("ALC", 10), "torrevieja": ("ALC", 45), "benidorm": ("ALC", 55),
    "orihuela": ("ALC", 50), "guardamar": ("ALC", 35), "santa pola": ("ALC", 30),
    "elche": ("ALC", 15), "elx": ("ALC", 15), "denia": ("ALC", 95),
    "moraira": ("ALC", 85), "calpe": ("ALC", 75), "altea": ("ALC", 65),
    "moralet": ("ALC", 20),
    # Costa Cálida / Murcia
    "murcia": ("RMU", 25), "cartagena": ("RMU", 45), "los alcazares": ("RMU", 30),
    "mazarron": ("RMU", 55), "aguilas": ("RMU", 80), "huercal-overa": ("RMU", 65),
    "huercal overa": ("RMU", 65), "cuevas del almanzora": ("RMU", 75),
    "san pedro del pinatar": ("RMU", 20), "los urrutias": ("RMU", 35),
    # Valencia
    "valencia": ("VLC", 8), "gandia": ("VLC", 65), "cullera": ("VLC", 40),
    # Bilbao / Baszkföld
    "bilbao": ("BIO", 10), "san sebastian": ("BIO", 95),
    # Huelva / Sevilla (Málaga repterétől messze)
    "bonares": ("AGP", 160), "huelva": ("AGP", 170),
}

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Hírlevelek / nem ingatlan ajánlatok kiszűrése (tárgy alapján)
SKIP_SUBJECT_PATTERNS = [
    r"está pasando",
    r"buying vs renting",
    r"popular properties this week",
    r"listings recommended for you",
    r"one of your favourites is no longer",
    r"price of this listing has gone",  # áresés kedvencekből → külön kezeljük
]

# ── Auth ──────────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("gmail", "v1", credentials=creds)

# ── State ─────────────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"processed_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ── Gmail ─────────────────────────────────────────────────────────────────────

def get_label_id(service, label_name):
    labels = service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]
    return None

def fetch_new_messages(service, label_id, state):
    result = service.users().messages().list(
        userId="me",
        labelIds=[label_id],
        q="is:unread",
        maxResults=50
    ).execute()
    messages = result.get("messages", [])
    processed = set(state.get("processed_ids", []))
    return [m for m in messages if m["id"] not in processed]

def get_message_details(service, msg_id):
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    body = extract_body(msg["payload"])
    snippet    = msg.get("snippet", "")
    all_links  = extract_all_property_links(body)
    ts_props   = parse_thinkspain_properties(body) if "thinkspain" in headers.get("From","").lower() else []
    link       = all_links[0] if all_links else ""
    return {
        "id":        msg_id,
        "subject":   headers.get("Subject", ""),
        "sender":    headers.get("From", ""),
        "date":      headers.get("Date", ""),
        "body":      html_to_text(body)[:4000],
        "snippet":   snippet,
        "link":      link,
        "all_links": all_links,
        "ts_props":  ts_props,   # ThinkSpain: [{link, title, price}, ...]
    }

def html_to_text(html):
    """HTML → plain text: CSS/style blokkok eltávolítása, entitások dekódolása."""
    if not html or not html.strip().startswith("<"):
        return html
    # Style és script blokkok eltávolítása
    html = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # HTML tagek eltávolítása
    text = re.sub(r'<[^>]+>', ' ', html)
    # HTML entitások
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace(
        '&lt;', '<').replace('&gt;', '>').replace('&euro;', '€').replace(
        '&#39;', "'").replace('&quot;', '"').replace('&aacute;', 'á').replace(
        '&eacute;', 'é').replace('&iacute;', 'í').replace('&oacute;', 'ó').replace(
        '&uacute;', 'ú').replace('&ntilde;', 'ñ').replace('&Aacute;', 'Á').replace(
        '&Ntilde;', 'Ñ').replace('&iexcl;', '¡').replace('&iquest;', '¿')
    # Whitespace normalizálás
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in payload["parts"]:
            data = part["body"].get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""

def parse_thinkspain_properties(html):
    """
    ThinkSpain email HTML-ből kinyeri az ingatlan párokat: {link, title, price}.
    Minden ingatlan 3x szerepel ugyanazzal a linkkel → egyedi ID alapján csoportosítunk.
    """
    pattern = r'href=["\']([^"\']*thinkspain\.com/property-for-sale/(\d+)[^"\']*)["\'][^>]*>\s*([^<]{0,120})'
    seen_ids = {}
    for url, prop_id, text in re.findall(pattern, html):
        text = text.strip()
        if prop_id not in seen_ids:
            seen_ids[prop_id] = {"link": url, "title": "", "price": ""}
        if "€" in text or text.startswith("€"):
            seen_ids[prop_id]["price"] = text.strip()
        elif text and "for sale in" in text.lower():
            seen_ids[prop_id]["title"] = text.strip()
    return list(seen_ids.values())

def extract_all_property_links(html):
    """Összes egyedi ingatlan link kinyerése egy emailből."""
    links = []
    seen  = set()

    patterns = [
        r'https?://(?:www\.)?idealista\.com/(?:en/)?inmueble/\d+/[^\s"\'<>]*',
        r'https?://(?:www\.)?kyero\.com/[^\s"\'<>]*property/\d+[^\s"\'<>]*',
        r'https?://(?:www\.)?thinkspain\.com/property-for-sale/\d+[^\s"\'<>]*',
        r'https?://(?:www\.)?fotocasa\.es/[^\s"\'<>]*\d+[^\s"\'<>]*',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html):
            url = m.group(0).rstrip(">,")
            # Egyedi ID kinyerése (duplikátum szűrés)
            id_match = re.search(r'/(\d+)', url)
            key = id_match.group(1) if id_match else url
            if key not in seen:
                seen.add(key)
                links.append(url)
    return links

def extract_property_link(text):
    """Visszaadja az első ingatlan linket (kompatibilitás)."""
    links = extract_all_property_links(text)
    return links[0] if links else ""

# ── Szűrés ────────────────────────────────────────────────────────────────────

def identify_portal(sender):
    s = sender.lower()
    for p in ALL_PORTALS:
        if p in s:
            return p
    return "ismeretlen"

def is_spanish_portal(sender):
    s = sender.lower()
    return any(p in s for p in PORTALS)

def is_newsletter(subject):
    """Hírlevelek és nem-ajánlat emailek kiszűrése."""
    s = subject.lower()
    return any(re.search(p, s) for p in SKIP_SUBJECT_PATTERNS)

# ── Geo számítások ────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Két pont közötti távolság km-ben (Haversine formula)."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def extract_main_city(city_name):
    """Teljes cím string-ből kinyeri a tényleges városnevet (utolsó vessző utáni rész)."""
    if not city_name:
        return city_name
    # "Calle X, Barrio Y, Ciudad" → "Ciudad"
    parts = [p.strip() for p in city_name.split(",")]
    # Az utolsó rész a legtöbbször a tényleges város
    # Ha csak egy rész van, azt adjuk vissza
    return parts[-1].strip() if len(parts) > 1 else parts[0].strip()

def geocode_city(city_name, country="Spain"):
    """Város koordinátáinak lekérése Nominatim-tól (OpenStreetMap)."""
    # Valódi település típusok (szigetek, vizek kizárva)
    GOOD_TYPES = {"city", "town", "village", "hamlet", "municipality", "suburb", "quarter", "neighbourhood"}
    BAD_TYPES  = {"islet", "island", "water", "bay", "coastline", "cape", "beach"}
    # Próbálkozási sorrend: teljes string → első rész (kis falu) → utolsó rész (önkormányzat)
    parts = [p.strip() for p in city_name.split(",")]
    candidates = [city_name]
    if len(parts) > 1:
        candidates = [city_name, parts[0], parts[-1]]  # "Isla Plana, Cartagena" → mind a három
    for name in candidates:
        query = urllib.parse.quote(name)
        url   = (
            f"https://nominatim.openstreetmap.org/search"
            f"?q={query}&format=json&limit=5&countrycodes=es&addressdetails=0"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "openclaw-ingatlan-watcher/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
                if not data:
                    continue
                # 1. preferencia: valódi település, nem sziget/víz
                best = next(
                    (r for r in data
                     if r.get("type") in GOOD_TYPES and r.get("type") not in BAD_TYPES),
                    None
                )
                # 2. preferencia: bármi, ami nem sziget/víz
                if best is None:
                    best = next(
                        (r for r in data if r.get("type") not in BAD_TYPES),
                        None
                    )
                if best is None:
                    continue
                log.info(f"[Geo] '{name}' → {best['display_name'][:70]}")
                return float(best["lat"]), float(best["lon"])
        except Exception as e:
            log.warning(f"[Geo] Nominatim hiba ({name}): {e}")
    return None, None

def nearest_airport(lat, lon):
    """Legközelebbi reptér és távolsága."""
    best_code, best_name, best_km = None, None, 9999
    for code, (alat, alon, name) in AIRPORTS.items():
        km = haversine(lat, lon, alat, alon)
        if km < best_km:
            best_km, best_code, best_name = km, code, name
    return best_code, best_name, round(best_km)

def nearest_coast_km(lat, lon):
    """Becsült távolság a legközelebbi tengerparti ponttól."""
    return round(min(haversine(lat, lon, clat, clon) for clat, clon in COAST_POINTS))

def nearest_ikea_km(lat, lon):
    """Legközelebbi IKEA távolsága km-ben."""
    return round(min(haversine(lat, lon, ilat, ilon) for ilat, ilon, _ in IKEA_STORES))

# Lidl boltok cache fájlja — ugyanott mint a DB és egyéb adatfájlok (DATA_DIR)
LIDL_CACHE_FILE = DATA_DIR / "lidl_stores.json"

# Képek könyvtára — ugyanaz mint a dashboardban (DATA_DIR/images)
IMAGES_DIR = DATA_DIR / "images"

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

def _find_image_parts(payload):
    """Rekurzívan bejárja a MIME fát és visszaadja az image/* részeket."""
    mime = payload.get("mimeType", "")
    if mime.startswith("image/"):
        yield payload
    for part in payload.get("parts", []):
        yield from _find_image_parts(part)

def extract_and_save_email_image(service, msg_id, prop_id):
    """
    Kibányássza az email első képét és elmenti IMAGES_DIR/<prop_id>.<ext> fájlba.
    Frissíti az adatbázis image_path mezőjét.
    Visszatér a fájlnévvel, vagy None-nal ha nincs kép.
    """
    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()
        for part in _find_image_parts(msg["payload"]):
            mime = part.get("mimeType", "")
            ext = MIME_TO_EXT.get(mime, ".jpg")
            body = part.get("body", {})
            data = body.get("data")
            if not data:
                attachment_id = body.get("attachmentId")
                if not attachment_id:
                    continue
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=attachment_id
                ).execute()
                data = att.get("data")
            if not data:
                continue
            image_bytes = base64.urlsafe_b64decode(data)
            # Min. 5 KB — ikonokat és spacer pixel-eket kiszűri
            if len(image_bytes) < 5 * 1024:
                continue
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"{prop_id}{ext}"
            with open(IMAGES_DIR / filename, "wb") as f:
                f.write(image_bytes)
            # DB frissítés
            import sqlite3
            from db import get_db_connection
            conn = get_db_connection()
            conn.execute("UPDATE properties SET image_path = ? WHERE id = ?", (filename, prop_id))
            conn.commit()
            conn.close()
            log.info(f"[Kép] Mentve: {filename} ({len(image_bytes)//1024} KB)")
            return filename
    except Exception as e:
        log.warning(f"[Kép] Nem sikerült kinyerni: {e}")
    return None

def load_lidl_stores():
    """Lidl boltok koordinátáinak betöltése — cache fájlból vagy Overpass API-ból."""
    if LIDL_CACHE_FILE.exists():
        try:
            with open(LIDL_CACHE_FILE, encoding="utf-8") as f:
                stores = json.load(f)
            if stores:
                log.info(f"[Lidl] {len(stores)} bolt betöltve a cache-ből.")
                return stores
        except Exception:
            pass

    log.info("[Lidl] Cache nem található, letöltés Overpass API-ból...")
    query = """
[out:json][timeout:60];
area["ISO3166-1"="ES"][admin_level=2]->.es;
node["shop"="supermarket"]["brand"="Lidl"](area.es);
out body;
"""
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "IngatlanMonitor/1.0 (tipcsy@gmail.com)",
            }
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
        stores = [
            (el["lat"], el["lon"])
            for el in result.get("elements", [])
            if el.get("type") == "node"
        ]
        if stores:
            with open(LIDL_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(stores, f)
            log.info(f"[Lidl] {len(stores)} bolt letöltve és elmentve.")
        return stores
    except Exception as e:
        log.error(f"[Lidl] Overpass hiba: {e}")
        return []

# Lidl boltok betöltése induláskor
_LIDL_STORES = None

def get_lidl_stores():
    global _LIDL_STORES
    if _LIDL_STORES is None:
        _LIDL_STORES = load_lidl_stores()
    return _LIDL_STORES

def nearest_lidl_km(lat, lon):
    """Legközelebbi Lidl távolsága km-ben, vagy None ha nincs adat."""
    stores = get_lidl_stores()
    if not stores:
        return None
    return round(min(haversine(lat, lon, slat, slon) for slat, slon in stores))

def geo_lookup(city):
    """Városnév alapján reptér, tenger, IKEA és Lidl távolság becslése."""
    if not city or city in ("?", "ismeretlen", "Costa del Sol"):
        return None, None, None, None, None, None
    lat, lon = geocode_city(city)
    if lat is None:
        return None, None, None, None, None, None
    apt_code, apt_name, apt_km = nearest_airport(lat, lon)
    sea_km = nearest_coast_km(lat, lon)
    ikea_km = nearest_ikea_km(lat, lon)
    lidl_km = nearest_lidl_km(lat, lon)
    log.info(f"[Geo] {city} → reptér: {apt_code} {apt_km} km | tenger: ~{sea_km} km | IKEA: ~{ikea_km} km | Lidl: ~{lidl_km} km")
    return apt_code, apt_km, sea_km, (lat, lon), ikea_km, lidl_km

# ── AI értékelés ──────────────────────────────────────────────────────────────

def load_rules():
    if RULES_FILE.exists():
        return RULES_FILE.read_text(encoding="utf-8")
    return ""

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# IKEA áruházak Spanyolországban (lat, lon, város)
IKEA_STORES = [
    (40.4165, -3.7026, "Madrid - Alcorcón"),
    (40.5194, -3.6374, "Madrid - San Sebastián de los Reyes"),
    (40.3833, -3.6500, "Madrid - Leganés"),
    (40.4650, -3.5880, "Madrid - Vallecas"),
    (41.3784, 2.1399,  "Barcelona - L'Hospitalet"),
    (41.4270, 2.2290,  "Barcelona - Badalona"),
    (41.5450, 2.1040,  "Barcelona - Sabadell"),
    (39.4699, -0.3763, "Valencia"),
    (37.3827, -5.9732, "Sevilla"),
    (43.2965, -1.9760, "Bilbao - Barakaldo"),
    (43.3619, -5.8444, "Oviedo - Llanera"),
    (43.3209, -8.4461, "A Coruña"),
    (37.9092, -4.7796, "Córdoba"),
    (40.6430, -3.1670, "Alcalá de Henares"),
    (38.0056, -1.1709, "Murcia"),
    (28.1248,-15.4300, "Las Palmas (Gran Canaria)"),
    (28.4636,-16.2518, "Santa Cruz de Tenerife"),
    (41.5718,  2.0330, "Terrassa"),
]

# Reptér koordináták (lat, lon, név) — csak Budapest közvetlen járattal!
AIRPORTS = {
    "AGP": (36.6749, -4.4990, "Málaga"),
    "ALC": (38.2822, -0.5582, "Alicante"),
    "RMU": (37.8030, -1.1253, "Murcia-Corvera"),
    "VLC": (39.4893, -0.4816, "Valencia"),
    "BIO": (43.3011, -2.9106, "Bilbao"),
}

# Spanyol tengerparti régiók közelítő pontjai (lat, lon)
# Ezeket használjuk ha nincs jobb adat
COAST_POINTS = [
    # Costa del Sol
    (36.7213, -4.4216), (36.5101, -4.8826), (36.3932, -5.1672),
    # Costa Blanca
    (38.3452, -0.4815), (37.9786, -0.6822), (38.1010, -0.7321),
    # Costa Cálida
    (37.6367, -0.9979), (37.5694, -1.0021), (37.8547, -1.3342),
    # Valencia
    (39.4561, -0.3274), (39.1701, -0.1654),
    # Costa Brava / Barcelona
    (41.3809,  2.1228), (41.7281,  2.9320),
]

def evaluate_with_ai(details):
    """
    Ollama helyi AI-val értékeli ki az ingatlant a RULES.md alapján.
    Visszatér egy dict-tel: properties lista
    """
    rules = load_rules()

    # ThinkSpain: strukturált lista link+cím+ár párokkal
    ts_props = details.get("ts_props", [])
    if ts_props:
        links_str = "\n".join(
            f"- {p['link']} | {p['title']} | {p['price']}"
            for p in ts_props
        )
    else:
        links_str = "\n".join(f"- {l}" for l in details.get("all_links", [])) or "none found"

    prompt = f"""You are a real estate filter AI. Evaluate a property listing email based on the rules below.

## RULES
{rules}

## EMAIL DATA
Portal: {identify_portal(details['sender'])}
Subject: {details['subject']}
Date: {details['date']}
Snippet: {details['snippet']}

PROPERTY LINKS FOUND IN EMAIL (use these exactly, match each property to its link):
{links_str}

Body:
{details['body'][:3000]}

## TASK
1. Identify ALL properties mentioned in this email (could be 1 or more)
2. For each property provide:
   - city: location name — for small villages use "Village, Municipality" format (e.g. "Isla Plana, Cartagena" or "Benahadux, Almería"). For large cities just the city name is fine.
   - price_eur: price as integer (0 if unknown)
   - size_m2: living area in m² as integer (0 if unknown)
   - garden_m2: garden area in m² as integer (null if unknown or no garden)
   - sea_km: distance to sea in km as number (null if unknown)
   - parking: "igen" / "nem" / "ismeretlen"
   - garden: "igen" / "nem" / "ismeretlen"
   - has_garage: true if the listing explicitly mentions a garage, false otherwise
   - legal_status: "ok" / "kizárt" / "kérdéses"
   - score: integer 1-10 based on the scoring rules (0 if EXCLUDED)
   - reason: 1-2 sentence explanation in Hungarian
   - description_hu: a 3-5 sentence Hungarian summary of the key property features (size, garden, garage, location highlights, condition, special features). Translate the most important details from the original listing text.
   - link: property URL if found in email, else empty string

Airports to check distance from (max 100km):
- Malaga (AGP) - Costa del Sol
- Alicante (ALC) - Costa Blanca
- Murcia-Corvera (RMU) - Costa Calida
- Valencia (VLC) - Valencia region
- Bilbao (BIO) - Basque Country

IMPORTANT: Respond ONLY with valid JSON, no extra text:
{{
  "properties": [
    {{
      "city": "...",
      "price_eur": 0,
      "size_m2": 0,
      "garden_m2": null,
      "sea_km": null,
      "airport": "AGP/ALC/RMU/VLC/BIO or null",
      "airport_km": null,
      "parking": "igen/nem/ismeretlen",
      "garden": "igen/nem/ismeretlen",
      "has_garage": false,
      "legal_status": "ok/kizárt/kérdéses",
      "score": 0,
      "reason": "...",
      "description_hu": "...",
      "link": ""
    }}
  ]
}}"""

    try:
        data = json.dumps({
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            text = result.get("response", "").strip()

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            log.warning(f"[AI] JSON nem található a válaszban: {text[:200]}")
            return None

    except Exception as e:
        log.error(f"[AI] Hiba: {e}")
        return None

# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("[Telegram] Nincs konfig (TELEGRAM_TOKEN/CHAT_ID hiányzik), kihagyva.")
        return False
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     message,
        "parse_mode":               "HTML",
        "disable_web_page_preview": False,
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            log.info(f"[Telegram] Elküldve (HTTP {resp.status})")
            return True
    except Exception as e:
        log.error(f"[Telegram] Hiba: {e}")
        return False

def parse_email_date(date_str):
    """Email dátum string → olvasható formátum."""
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str[:16] if date_str else "?"

def format_telegram_message(details, prop):
    portal = identify_portal(details["sender"])
    score  = prop.get("score", 0)
    stars  = "⭐" * min(int(score), 10)

    # CSAK a details["link"]-et használjuk — az AI-tól jövő linket eldobjuk
    link = details["link"] or ""

    email_date = parse_email_date(details.get("date", ""))

    lines = [
        f"🏠 <b>Új ingatlan — {score}/10 pont</b> {stars}",
        f"📍 <b>{prop.get('city', 'ismeretlen')}</b>",
        f"💶 <b>{prop.get('price_eur', '?'):,} €</b>",
    ]
    if prop.get("size_m2"):
        lines.append(f"📐 {prop['size_m2']} m²")
    if prop.get("sea_km") is not None:
        lines.append(f"🌊 Tenger: ~{prop['sea_km']} km")
    if prop.get("airport") and prop.get("airport_km") is not None:
        apt_name = AIRPORTS.get(prop["airport"], ("","",""))[2]
        lines.append(f"✈️ {prop['airport']} ({apt_name}): ~{prop['airport_km']} km")

    parking = {"igen": "✅", "nem": "❌", "ismeretlen": "❓"}.get(prop.get("parking", ""), "❓")
    garden  = {"igen": "✅", "nem": "❌", "ismeretlen": "❓"}.get(prop.get("garden", ""), "❓")
    lines.append(f"🚗 Parkolás: {parking}  🌿 Kert: {garden}")

    legal = prop.get("legal_status", "ok")
    if legal == "kizárt":
        lines.append("⛔ <b>Jogi státusz: KIZÁRT</b>")
    elif legal == "kérdéses":
        lines.append("⚠️ Jogi státusz: kérdéses")

    lines.append(f"📬 {portal}  |  📅 {email_date}")
    lines.append(f"💬 {prop.get('reason', '')}")

    # Linkek szekció
    lines.append("")  # üres sor
    if link:
        lines.append(f"🔗 <a href=\"{link}\">Ingatlan megtekintése</a>")

    # Térkép link (ha van koordináta)
    coords = prop.get("coords")
    if coords and coords[0] and coords[1]:
        lat, lon = coords
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        lines.append(f"🗺️ <a href=\"{maps_url}\">Térkép megnyitása</a>")

    # Email link (Gmail)
    email_id = details.get("id")
    if email_id:
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{email_id}"
        lines.append(f"📧 <a href=\"{gmail_url}\">Eredeti email</a>")

    return "\n".join(lines)

# ── Fő logika ─────────────────────────────────────────────────────────────────

def process_message(details, service=None):
    log.info(f"{'─'*60}")
    log.info(f"Email: {details['subject'][:70]}")
    log.info(f"Portal: {identify_portal(details['sender'])}")

    result = evaluate_with_ai(details)
    if not result:
        log.warning("[AI] Értékelés sikertelen, kihagyva.")
        return 0

    properties = result.get("properties", [])
    sent = 0

    for prop in properties:
        score = prop.get("score", 0)
        legal = prop.get("legal_status", "ok")
        city  = prop.get("city", "?")

        # Geo lookup — Nominatim alapján pontos számítás
        apt_code, apt_km, sea_km, coords, ikea_km, lidl_km = geo_lookup(city)
        if apt_code:
            prop["airport"]    = apt_code
            prop["airport_km"] = apt_km
        if sea_km is not None and not prop.get("sea_km"):
            prop["sea_km"] = sea_km
        if ikea_km is not None:
            prop["ikea_km"] = ikea_km
        if lidl_km is not None:
            prop["lidl_km"] = lidl_km
        # Koordináták mentése a térkép linkhez
        if coords:
            prop["coords"] = coords

        # Fallback a statikus táblázatból ha a Nominatim sem ment
        if not prop.get("airport") or not prop.get("airport_km"):
            city_key = city.lower().strip()
            for key, (apt, km) in CITY_AIRPORT_MAP.items():
                if key in city_key or city_key in key:
                    prop["airport"]    = apt
                    prop["airport_km"] = km
                    break

        log.info(f"Ingatlan: {city} | {prop.get('price_eur', '?')} EUR | {score}/10 | {prop.get('reason', '')[:60]}")

        if legal == "kizárt":
            log.info(f"Kizárt jogi státusz, kihagyva: {city}")
            continue

        # Link párosítás
        all_links = details.get("all_links", [])
        ts_props  = details.get("ts_props", [])
        ai_link   = prop.get("link", "")
        matched_link = ""

        if ts_props:
            # ThinkSpain: városnév alapján keresünk a strukturált listában
            city_lower = city.lower()
            for tp in ts_props:
                if any(word in tp["title"].lower() for word in city_lower.split() if len(word) > 3):
                    matched_link = tp["link"]
                    break
            # Ha nem találtuk, az AI linkjét ellenőrizzük
            if not matched_link and ai_link:
                id_match = re.search(r'/(\d+)', ai_link)
                if id_match:
                    prop_id = id_match.group(1)
                    for tp in ts_props:
                        if prop_id in tp["link"]:
                            matched_link = tp["link"]
                            break

        if not matched_link:
            # Általános: AI linkje szerepel-e az emailben?
            if ai_link and any(ai_link in l or l in ai_link for l in all_links):
                matched_link = next((l for l in all_links if ai_link in l or l in ai_link), ai_link)
            elif all_links:
                idx = list(properties).index(prop)
                matched_link = all_links[idx] if idx < len(all_links) else all_links[0]

        if not matched_link:
            log.warning(f"Nincs valódi link az emailben, kihagyva: {city}")
            continue
        details["link"] = matched_link

        # Gmail URL generálása
        msg_id = details.get("id")
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}" if msg_id else ""

        # Egyedi email_id: message_id + URL hash (ha több ingatlan van egy emailben)
        url_hash = str(abs(hash(matched_link)))[:8]
        email_id = f"{msg_id}_{url_hash}" if msg_id else f"manual_{url_hash}"

        # Minden értékelt ingatlant mentjük az adatbázisba
        try:
            row_id = save_property(
                email_id=email_id,
                email_date=details.get("date", ""),
                portal=identify_portal(details["sender"]),
                prop=prop,
                property_url=matched_link,
                gmail_url=gmail_url,
                original_text=details.get("body", ""),
            )
            if row_id and service:
                extract_and_save_email_image(service, msg_id, row_id)
        except Exception as e:
            log.error(f"[DB] Mentési hiba ({city}): {e}")

        if score >= 7:
            log.info(f"Telegram értesítő küldése: {city} | {score}/10")
            msg = format_telegram_message(details, prop)
            send_telegram(msg)
            sent += 1
        elif score >= 5:
            log.info(f"{score}/10 — Megfelel, Telegram értesítő nem szükséges: {city}")
        else:
            log.info(f"{score}/10 — Nem felel meg: {city}")

    return sent

def run():
    log.info(f"{'='*60}")
    log.info(f"Gmail Ingatlan Watcher indul — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*60}")

    # Adatbázis inicializálása
    init_db()

    service = get_gmail_service()
    state   = load_state()

    label_id = get_label_id(service, GMAIL_LABEL)
    if not label_id:
        log.error(f"'{GMAIL_LABEL}' Gmail mappa nem található!")
        return

    new_messages = fetch_new_messages(service, label_id, state)
    log.info(f"{len(new_messages)} új üzenet a mappában.")

    processed_ids  = list(state.get("processed_ids", []))
    total_sent     = 0
    total_skipped  = 0
    total_analyzed = 0

    for msg in new_messages:
        details = get_message_details(service, msg["id"])
        processed_ids.append(msg["id"])

        # Nem spanyol portál
        if not is_spanish_portal(details["sender"]):
            total_skipped += 1
            log.info(f"[SKIP] Nem spanyol portál: {details['sender'][:50]}")
            continue

        # Hírlevél / nem ajánlat
        if is_newsletter(details["subject"]):
            total_skipped += 1
            log.info(f"[SKIP] Hírlevél: {details['subject'][:60]}")
            continue

        total_analyzed += 1
        sent = process_message(details, service=service)
        total_sent += sent

    # State mentése
    state["processed_ids"] = processed_ids[-500:]
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    log.info(f"{'='*60}")
    log.info(f"Kész! Elemzett: {total_analyzed} | Telegram értesítő: {total_sent} | Kihagyva: {total_skipped}")
    log.info(f"{'='*60}")

if __name__ == "__main__":
    run()
