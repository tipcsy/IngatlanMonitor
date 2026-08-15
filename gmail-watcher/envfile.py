"""
Konfiguráció betöltése .env fájlból — külső függőség nélkül.

Miért külön modul? Mert a betöltésnek MINDEN olyan modul előtt le kell futnia,
amelyik import-időben olvas környezeti változót (pl. db.py). Ha a betöltés a
belépési pontban ül, de az importok előrébb vannak, a .env értékei már nem
érnek el a modulokhoz — csendben a beégetett alapértékekre esik vissza minden.

Használat (a modul tetején, minden más import előtt):

    from envfile import require, optional

A betöltés magától lefut az első importkor, és csak egyszer. Meglévő
környezeti változót SOHA nem ír felül: a Docker/compose által átadott érték
mindig erősebb a .env fájlnál.
"""

import os
from pathlib import Path

_loaded = False


def load_env() -> None:
    """A .env beolvasása: előbb a modul mellől, aztán a projekt gyökeréből."""
    global _loaded
    if _loaded:
        return

    here = Path(__file__).resolve().parent
    for env_file in (here / ".env", here.parent / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)

    _loaded = True


def require(name: str, hint: str = "") -> str:
    """Kötelező beállítás. Ha hiányzik, azonnal és beszédesen elszáll."""
    value = os.environ.get(name, "").strip()
    if not value:
        extra = f" ({hint})" if hint else ""
        raise RuntimeError(
            f"Hiányzó kötelező beállítás: {name}{extra}.\n"
            f"Másold le a .env.example fájlt .env néven a projekt gyökerébe, "
            f"és töltsd ki. A .env nincs verziókövetve."
        )
    return value


def optional(name: str, default: str = "") -> str:
    """Nem kötelező beállítás alapértelmezéssel. Titkot ide SOHA ne tegyél."""
    value = os.environ.get(name, "").strip()
    return value if value else default


load_env()
