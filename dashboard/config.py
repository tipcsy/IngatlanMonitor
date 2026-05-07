"""
Dashboard konfiguráció
"""

import os
from pathlib import Path

# Adatbázis elérési út
# Docker-ben: /app/data/ingatlan.db
# Lokálisan: ../data/ingatlan.db
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
DATABASE = DATA_DIR / "ingatlan.db"

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
