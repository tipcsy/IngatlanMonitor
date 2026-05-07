"""Test az uj Telegram uzenet formatummal."""
import sys
# Windows konzol UTF-8 tamogatas
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, ".")

from gmail_watcher import load_env, send_telegram, format_telegram_message

load_env()

# Teszt adatok
test_details = {
    "id": "18f1234567890abc",
    "sender": "alerts@kyero.com",
    "date": "Sat, 05 Apr 2026 12:00:00 +0200",
    "subject": "New property in Torrevieja",
    "link": "https://www.kyero.com/en/property/12345",
}

test_prop = {
    "city": "Torrevieja",
    "price_eur": 145000,
    "size_m2": 120,
    "sea_km": 2,
    "airport": "ALC",
    "airport_km": 45,
    "parking": "igen",
    "garden": "igen",
    "legal_status": "ok",
    "score": 8,
    "reason": "Kiváló ár-érték arány, közel a tengerhez, saját parkoló és kert.",
    "coords": (37.9786, -0.6822),  # Torrevieja koordinatak
}

print("Generalt uzenet:\n")
print("="*60)
msg = format_telegram_message(test_details, test_prop)
print(msg)
print("="*60)

# Kuldes Telegramra
print("\nKuldes Telegramra...")
if send_telegram(msg):
    print("Sikeres!")
else:
    print("Sikertelen!")
