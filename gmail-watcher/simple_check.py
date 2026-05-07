#!/usr/bin/env python3
"""
Egyszerű Gmail 'ingatlan' mappa ellenőrzése az elmúlt 24 órára
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent
CLIENT_SECRET = BASE_DIR / "client_secret.json"
GMAIL_LABEL = "Hírlevelek/Ingatlan"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def safe_print(text):
    """Biztonságos nyomtatás, elkerüli a karakterkódolási problémákat"""
    try:
        print(text.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
    except:
        print(str(text).encode('ascii', errors='replace').decode('ascii', errors='replace'))

def get_gmail_service():
    """Service Account autentikáció"""
    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(f"Google Service Account kulcs nem található: {CLIENT_SECRET}")
    creds = service_account.Credentials.from_service_account_file(
        str(CLIENT_SECRET), scopes=SCOPES
    )
    return build("gmail", "v1", credentials=creds)

def get_label_id(service, label_name):
    labels = service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]
    return None

def get_last_24h_messages(service, label_id):
    """Az elmúlt 24 órában érkezett üzenetek lekérdezése"""
    after_date = (datetime.now() - timedelta(hours=24)).strftime("%Y/%m/%d")
    query = f"after:{after_date}"
    
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=[label_id],
            q=query,
            maxResults=50
        ).execute()
        return result.get("messages", [])
    except Exception as e:
        safe_print(f"Hiba a levelek lekérdezésekor: {e}")
        return []

def get_message_subject(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    return headers.get("Subject", "No subject")

def identify_portal(sender):
    s = sender.lower()
    portals = ["idealista.com", "kyero.com", "thinkspain.com", "fotocasa.es"]
    for p in portals:
        if p in s:
            return p
    return "ismeretlen"

def main():
    safe_print("=" * 60)
    safe_print("Gmail 'ingatlan' mappa ellenorzes (elmult 24 ora)")
    safe_print("=" * 60)
    
    try:
        service = get_gmail_service()
        label_id = get_label_id(service, GMAIL_LABEL)
        
        if not label_id:
            safe_print(f"Hiba: '{GMAIL_LABEL}' mappa nem talalhato!")
            return
        
        messages = get_last_24h_messages(service, label_id)
        safe_print(f"\nTalalt uzenetek: {len(messages)}")
        
        if not messages:
            safe_print("\nNincs uj ingatlan")
            return
        
        # Csak a tárgyakat listázzuk ki
        for i, msg in enumerate(messages, 1):
            subject = get_message_subject(service, msg["id"])
            safe_print(f"{i}. {subject}")
        
        safe_print(f"\nOsszesen: {len(messages)} uzenet az elmult 24 oraban")
        
    except Exception as e:
        safe_print(f"Hiba tortent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()