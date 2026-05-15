"""
Dashboard konfiguráció
"""

import os
from pathlib import Path

# Adat könyvtár (képek, Lidl cache stb.)
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
IMAGES_DIR = DATA_DIR / "images"

# MariaDB kapcsolat
DB_HOST = os.environ.get("DB_HOST", "192.168.31.104")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "***REMOVED***")
DB_NAME = os.environ.get("DB_NAME", "ingatlan")

# Flask konfiguráció
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# Reptér → régió mapping (a szűrőkhöz)
REGIONS = {
    "AGP": "Costa del Sol",
    "ALC": "Costa Blanca",
    "RMU": "Costa Cálida",
    "VLC": "Valencia",
    "BIO": "País Vasco",
}

# Reptér nevek (tooltip-ekhez)
AIRPORT_NAMES = {
    "AGP": "Málaga",
    "ALC": "Alicante",
    "RMU": "Murcia-Corvera",
    "VLC": "Valencia",
    "BIO": "Bilbao",
}
