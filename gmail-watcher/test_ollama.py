"""
Ollama kapcsolat tesztelo szkript
=================================
Lokalisan teszteli az AI ertekeelest kulonbozo modellekkel.

Futtatas: python test_ollama.py
"""

import os
import sys
import json
import urllib.request
import time
from pathlib import Path

# Windows konzol UTF-8 tamogatas
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# .env betöltése
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

# Konfiguráció - lokális teszthez localhost
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi3:mini")

# Lokális teszt override
LOCAL_OLLAMA_URL = "http://localhost:11434"

def test_connection(url):
    """Teszteli az Ollama kapcsolatot."""
    print(f"\n{'='*60}")
    print(f"Ollama kapcsolat teszt: {url}")
    print(f"{'='*60}")

    try:
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            print(f"✅ Kapcsolat OK")
            print(f"📦 Elérhető modellek: {', '.join(models)}")
            return models
    except Exception as e:
        print(f"❌ Kapcsolat sikertelen: {e}")
        return []

def test_simple_json(url, model):
    """Egyszerű JSON válasz teszt."""
    print(f"\n{'─'*60}")
    print(f"Teszt 1: Egyszerű JSON ({model})")
    print(f"{'─'*60}")

    prompt = 'Return JSON: {"test": "ok", "number": 42}'

    start = time.time()
    try:
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()

        req = urllib.request.Request(
            f"{url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            response = result.get("response", "")
            elapsed = time.time() - start

            print(f"⏱️  Válaszidő: {elapsed:.1f} másodperc")
            print(f"📝 Válasz: {response[:200]}")

            # JSON validálás
            try:
                parsed = json.loads(response)
                print(f"✅ Érvényes JSON")
                return True, elapsed
            except:
                print(f"❌ Érvénytelen JSON!")
                return False, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Hiba ({elapsed:.1f}s): {e}")
        return False, elapsed

def test_property_evaluation(url, model):
    """Ingatlan értékelés teszt (realisztikus prompt)."""
    print(f"\n{'─'*60}")
    print(f"Teszt 2: Ingatlan értékelés ({model})")
    print(f"{'─'*60}")

    # Egyszerűsített prompt (a valódi prompt ennél hosszabb)
    prompt = """You are a real estate filter AI. Evaluate this property.

RULES:
- Max price: 170000 EUR
- Min size: 100 m2
- Max distance from sea: 30 km
- Must have parking
- Airports within 100km: Alicante (ALC), Malaga (AGP)

PROPERTY:
Villa in Torrevieja, Costa Blanca
Price: 145,000 EUR
Size: 120 m2 living area, 200 m2 plot
Features: Private parking, garden, near beach (2km)
Near Alicante airport (45km)

Return ONLY valid JSON:
{
  "properties": [
    {
      "city": "city name",
      "price_eur": 0,
      "size_m2": 0,
      "sea_km": null,
      "airport": "ALC/AGP or null",
      "airport_km": null,
      "parking": "igen/nem/ismeretlen",
      "garden": "igen/nem/ismeretlen",
      "score": 0,
      "reason": "Hungarian explanation"
    }
  ]
}"""

    start = time.time()
    try:
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()

        req = urllib.request.Request(
            f"{url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            response = result.get("response", "")
            elapsed = time.time() - start

            print(f"⏱️  Válaszidő: {elapsed:.1f} másodperc")

            # JSON validálás
            try:
                parsed = json.loads(response)
                print(f"✅ Érvényes JSON")

                props = parsed.get("properties", [])
                if props:
                    p = props[0]
                    print(f"📍 Város: {p.get('city', '?')}")
                    print(f"💶 Ár: {p.get('price_eur', '?')} EUR")
                    print(f"📐 Méret: {p.get('size_m2', '?')} m2")
                    print(f"⭐ Pontszám: {p.get('score', '?')}/10")
                    print(f"💬 Indoklás: {p.get('reason', '?')[:100]}")
                return True, elapsed
            except:
                print(f"❌ Érvénytelen JSON!")
                print(f"📝 Válasz: {response[:300]}")
                return False, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Hiba ({elapsed:.1f}s): {e}")
        return False, elapsed

def main():
    print("\n" + "="*60)
    print("  OLLAMA TESZT - Ingatlan Monitor")
    print("="*60)
    print(f"\n.env beállítások:")
    print(f"  OLLAMA_URL: {OLLAMA_URL}")
    print(f"  OLLAMA_MODEL: {OLLAMA_MODEL}")

    # 1. Lokális Ollama teszt
    local_models = test_connection(LOCAL_OLLAMA_URL)

    # 2. Szerver Ollama teszt (ha különbözik)
    if OLLAMA_URL != LOCAL_OLLAMA_URL:
        server_models = test_connection(OLLAMA_URL)
    else:
        server_models = local_models

    # 3. Modellek tesztelése lokálisan
    test_models = []
    if "phi3:mini" in local_models:
        test_models.append("phi3:mini")
    if "llama3.1:8b" in local_models:
        test_models.append("llama3.1:8b")
    if "mistral:latest" in local_models:
        test_models.append("mistral:latest")

    results = {}
    for model in test_models[:2]:  # Max 2 modellt tesztelünk
        print(f"\n\n{'#'*60}")
        print(f"# MODELL TESZT: {model}")
        print(f"{'#'*60}")

        ok1, t1 = test_simple_json(LOCAL_OLLAMA_URL, model)
        ok2, t2 = test_property_evaluation(LOCAL_OLLAMA_URL, model)

        results[model] = {
            "simple_ok": ok1,
            "simple_time": t1,
            "property_ok": ok2,
            "property_time": t2,
        }

    # Összefoglaló
    print(f"\n\n{'='*60}")
    print("  ÖSSZEFOGLALÓ")
    print(f"{'='*60}")

    for model, r in results.items():
        status = "✅" if r["property_ok"] else "❌"
        print(f"\n{status} {model}:")
        print(f"   Egyszerű JSON: {'OK' if r['simple_ok'] else 'FAIL'} ({r['simple_time']:.1f}s)")
        print(f"   Ingatlan teszt: {'OK' if r['property_ok'] else 'FAIL'} ({r['property_time']:.1f}s)")

    # Ajánlás
    print(f"\n{'─'*60}")
    print("AJÁNLÁS:")

    best_model = None
    for model, r in results.items():
        if r["property_ok"]:
            if best_model is None or r["property_time"] < results[best_model]["property_time"]:
                best_model = model

    if best_model:
        print(f"✅ Használd a '{best_model}' modellt!")
        print(f"   Módosítsd az .env fájlt: OLLAMA_MODEL={best_model}")
    else:
        print("❌ Egyik modell sem adott megfelelő választ.")
        print("   Próbáld meg a 'llama3.1:8b' vagy 'mistral:latest' modellt telepíteni.")

if __name__ == "__main__":
    main()
