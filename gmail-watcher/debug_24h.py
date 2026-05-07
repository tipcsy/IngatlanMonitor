#!/usr/bin/env python3
"""
Debug szkript az elmúlt 24 óra leveleinek megtekintésére
"""

import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64

BASE_DIR = Path(__file__).parent
CLIENT_SECRET = BASE_DIR / "client_secret.json"
GMAIL_LABEL = "Hírlevelek/Ingatlan"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

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

def get_last_24h_messages(service, label_id):
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
        print(f"Hiba a levelek lekérdezésekor: {e}")
        return []

def get_message_snippet(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
    return msg.get("snippet", "")

def main():
    print("=" * 80)
    print("DEBUG: Elmúlt 24 óra levelei")
    print("=" * 80)
    
    try:
        service = get_gmail_service()
        label_id = get_label_id(service, GMAIL_LABEL)
        
        if not label_id:
            print(f"Hiba: '{GMAIL_LABEL}' mappa nem található!")
            return
        
        messages = get_last_24h_messages(service, label_id)
        print(f"\nÖsszes üzenet: {len(messages)}")
        
        for i, msg in enumerate(messages, 1):
            snippet = get_message_snippet(service, msg["id"])
            print(f"\n{i}. ID: {msg['id']}")
            print(f"   Snippet: {snippet[:200]}...")
        
        print(f"\n{'='*80}")
        
        # Válasszunk egy emailt részletes megtekintésre
        if messages:
            print("\nRészletes tartalom (az első email):")
            print("-" * 80)
            
            # Teljes email lekérése
            msg = service.users().messages().get(
                userId="me", id=messages[0]["id"], format="full"
            ).execute()
            
            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            body = extract_body(msg["payload"])
            
            print(f"Tárgy: {headers.get('Subject', 'Nincs')}")
            print(f"Feladó: {headers.get('From', 'Nincs')}")
            print(f"Dátum: {headers.get('Date', 'Nincs')}")
            print(f"\nTartalom (első 1000 karakter):")
            print("-" * 80)
            print(body[:1000])
            print("-" * 80)
            
            # Ingatlan információk keresése
            print("\nKeresett információk:")
            
            # Ár
            price_matches = list(re.finditer(r'(\d{1,3}(?:[.,]\d{3})*)\s*€', body.replace(',', '')))
            if price_matches:
                print(f"Árak találva: {len(price_matches)}")
                for match in price_matches[:3]:
                    price = int(match.group(1).replace('.', ''))
                    print(f"  - {price:,} €")
            
            # Méret
            size_matches = list(re.finditer(r'(\d{1,4})\s*m²', body, re.IGNORECASE))
            if size_matches:
                print(f"Méretek találva: {len(size_matches)}")
                for match in size_matches[:3]:
                    print(f"  - {match.group(1)} m²")
            
            # Város/régió
            regions = ["malaga", "alicante", "valencia", "murcia", "bilbao", "costa del sol", "costa blanca"]
            found_regions = []
            for region in regions:
                if region in body.lower():
                    found_regions.append(region)
            if found_regions:
                print(f"Régiók találva: {', '.join(found_regions)}")
            
            # Linkek
            link_patterns = [
                r'https?://(?:www\.)?idealista\.com/(?:en/)?inmueble/\d+/[^\s"\']*',
                r'https?://(?:www\.)?kyero\.com/[^\s"\']*property/\d+[^\s"\']*',
            ]
            all_links = []
            for pattern in link_patterns:
                for match in re.finditer(pattern, body):
                    all_links.append(match.group(0).rstrip(">,"))
            
            if all_links:
                print(f"Ingatlan linkek találva: {len(all_links)}")
                for link in all_links[:2]:
                    print(f"  - {link}")
            
    except Exception as e:
        print(f"Hiba történt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()