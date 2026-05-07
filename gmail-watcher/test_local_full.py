"""
Teljes lokalis teszt az uj beallitasokkal
==========================================
Futtatas: python test_local_full.py
"""

import os
import sys

# Windows konzol UTF-8 tamogatas
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# OVERRIDE: lokalis Ollama hasznalata
os.environ["OLLAMA_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.1:8b"  # Jobb minosegu valaszok

sys.path.insert(0, ".")

from gmail_watcher import (
    load_env, get_gmail_service, get_label_id, fetch_new_messages,
    get_message_details, is_spanish_portal, is_newsletter, identify_portal,
    evaluate_with_ai, geo_lookup, format_telegram_message, send_telegram,
    load_state, GMAIL_LABEL, CITY_AIRPORT_MAP
)

def main():
    print("\n" + "="*60)
    print("  LOKÁLIS TESZT - Új beállításokkal")
    print("="*60)
    print(f"\nOLLAMA_URL: {os.environ.get('OLLAMA_URL')}")
    print(f"OLLAMA_MODEL: {os.environ.get('OLLAMA_MODEL')}")

    # .env betöltése (Telegram credentials)
    load_env()

    # Gmail kapcsolat
    print("\n1. Gmail kapcsolat...")
    try:
        service = get_gmail_service()
        print("   ✅ Gmail OK")
    except Exception as e:
        print(f"   ❌ Gmail hiba: {e}")
        print("   (Futtasd először a gmail_watcher.py-t a böngészős auth-hoz)")
        return

    # Label keresés
    print("\n2. Ingatlan mappa keresés...")
    label_id = get_label_id(service, GMAIL_LABEL)
    if label_id:
        print(f"   ✅ Mappa megtalálva: {GMAIL_LABEL}")
    else:
        print(f"   ❌ Mappa nem található: {GMAIL_LABEL}")
        return

    # Üzenetek lekérése (csak 1 db)
    print("\n3. Legutóbbi spanyol ingatlan email keresése...")
    state = load_state()
    all_messages = fetch_new_messages(service, label_id, state)

    # Keressük az első spanyol portál emailt
    test_msg = None
    for msg in all_messages[:10]:  # Max 10-et nézünk
        details = get_message_details(service, msg["id"])
        if is_spanish_portal(details["sender"]) and not is_newsletter(details["subject"]):
            test_msg = details
            break

    if not test_msg:
        print("   ⚠️  Nincs új spanyol ingatlan email. Teszt adatokkal folytatjuk.")
        # Fallback: teszt adatok
        test_msg = {
            "id": "test123",
            "sender": "alerts@kyero.com",
            "date": "Sat, 05 Apr 2026 12:00:00 +0200",
            "subject": "New villa in Torrevieja - 145000 EUR",
            "body": """New property alert from Kyero.com

Villa for sale in Torrevieja, Costa Blanca
Price: 145,000 EUR
Living area: 120 m2
Plot: 200 m2

Features:
- Private parking
- Garden
- 2 km from the beach
- Near Alicante airport (45 km)

https://www.kyero.com/en/property/12345
""",
            "snippet": "New villa in Torrevieja 145000 EUR",
            "link": "https://www.kyero.com/en/property/12345",
            "all_links": ["https://www.kyero.com/en/property/12345"],
            "ts_props": [],
        }
    else:
        print(f"   ✅ Találat: {test_msg['subject'][:50]}")
        print(f"   📬 Forrás: {identify_portal(test_msg['sender'])}")

    # AI értékelés
    print("\n4. AI értékelés (llama3.1:8b)...")
    print("   ⏳ Ez akár 1-2 percig is tarthat...")

    result = evaluate_with_ai(test_msg)

    if not result:
        print("   ❌ AI értékelés sikertelen")
        return

    properties = result.get("properties", [])
    if not properties:
        print("   ⚠️  Nincs ingatlan az AI válaszában")
        return

    print(f"   ✅ {len(properties)} ingatlan értékelve")

    # Első ingatlan feldolgozása
    prop = properties[0]
    city = prop.get("city", "?")

    print(f"\n5. Geo lookup: {city}")
    apt_code, apt_km, sea_km, coords = geo_lookup(city)
    if apt_code:
        prop["airport"] = apt_code
        prop["airport_km"] = apt_km
    if sea_km is not None and not prop.get("sea_km"):
        prop["sea_km"] = sea_km
    if coords:
        prop["coords"] = coords
        print(f"   ✅ Koordináták: {coords[0]:.4f}, {coords[1]:.4f}")

    # Fallback
    if not prop.get("airport"):
        city_key = city.lower().strip()
        for key, (apt, km) in CITY_AIRPORT_MAP.items():
            if key in city_key or city_key in key:
                prop["airport"] = apt
                prop["airport_km"] = km
                break

    # Link beállítás
    test_msg["link"] = test_msg.get("link") or (test_msg.get("all_links", [None])[0])

    # Telegram üzenet
    print("\n6. Telegram üzenet generálás...")
    msg = format_telegram_message(test_msg, prop)
    print("\n" + "-"*60)
    print(msg)
    print("-"*60)

    # Küldés
    print("\n7. Küldés Telegramra...")
    if send_telegram(msg):
        print("   ✅ Sikeres!")
    else:
        print("   ❌ Sikertelen")

    # Összefoglaló
    print("\n" + "="*60)
    print("  TESZT EREDMÉNY")
    print("="*60)
    print(f"  Város: {prop.get('city', '?')}")
    print(f"  Ár: {prop.get('price_eur', '?')} EUR")
    print(f"  Pontszám: {prop.get('score', '?')}/10")
    print(f"  Indoklás: {prop.get('reason', '?')[:80]}")
    print("="*60)

if __name__ == "__main__":
    main()
