"""Gyors Telegram teszt."""
import sys
sys.path.insert(0, ".")

from gmail_watcher import load_env, send_telegram
load_env()

send_telegram("🏠 <b>Teszt üzenet</b>\nA Gmail ingatlan watcher működik! ✅")
print("Kész!")
