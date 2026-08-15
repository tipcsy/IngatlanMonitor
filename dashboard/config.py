"""
Dashboard konfiguráció
"""

import os
import secrets
from pathlib import Path

# Ez az import tölti be a .env-et — minden környezetifüggő konstans előtt kell.
from envfile import require, optional

# Adat könyvtár (képek, Lidl cache stb.)
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
IMAGES_DIR = DATA_DIR / "images"

# MariaDB kapcsolat
DB_HOST = optional("DB_HOST", "localhost")
DB_PORT = int(optional("DB_PORT", "3306"))
DB_USER = optional("DB_USER", "ingatlan")
DB_PASSWORD = require("DB_PASSWORD", "a MariaDB jelszava")
DB_NAME = optional("DB_NAME", "ingatlan")

# Flask konfiguráció. Ha nincs megadva SECRET_KEY, indulásonként generálunk egyet:
# a munkamenetek újraindításkor elvesznek, de nem kerül gyenge, ismert kulcs a kódba.
SECRET_KEY = optional("SECRET_KEY") or secrets.token_hex(32)
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# Reptér → régió mapping (a szűrőkhöz)
REGIONS = {
    "AGP": "Costa del Sol",
    "ALC": "Costa Blanca",
    "RMU": "Costa Cálida",
    "VLC": "Valencia",
    "BIO": "País Vasco",
    "BRU": "Brüsszel környéke",
    "CRL": "Brüsszel környéke",
}

# Reptér nevek (tooltip-ekhez)
AIRPORT_NAMES = {
    "AGP": "Málaga",
    "ALC": "Alicante",
    "RMU": "Murcia-Corvera",
    "VLC": "Valencia",
    "BIO": "Bilbao",
    "BRU": "Brüsszel - Zaventem",
    "CRL": "Brüsszel - Charleroi",
}

# Országok — a dashboard ország-szűrőjéhez. Bővíthető pl. "NL": "Hollandia"-val, ha lesz rá portál.
COUNTRIES = {
    "ES": "Spanyolország",
    "BE": "Belgium",
}
