"""
Utolsó 24 óra Gmail 'ingatlan' mappájának ellenőrzése
"""
import os
import json
import base64
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from email.utils import parsedate_to_datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Konfiguráció ──────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent
CLIENT_SECRET = BASE_DIR / "client_secret.json"
STATE_FILE    = BASE_DIR / "state.json"

GMAIL_LABEL = "Hírlevelek/Ingatlan"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Auth ──────────────────────────────────────────────────────────────────────

def get_gmail_service():
    """Service Account autentikáció"""
    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(f"Google Service Account kulcs nem található: {CLIENT_SECRET}")
    creds = service_account.Credentials.from_service_account_file(
        str(CLIENT_SECRET), scopes=SCOPES
    )
    return build("gmail", "v1", credentials=creds)

# ── Gmail funkciók ────────────────────────────────────────────────────────────

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

def get_message_details(service, msg_id):
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    body = extract_body(msg["payload"])
    snippet = msg.get("snippet", "")
    
    # Extract links
    links = []
    patterns = [
        r'https?://(?:www\.)?idealista\.com/(?:en/)?inmueble/\d+/[^\s"\'<>]*',
        r'https?://(?:www\.)?kyero\.com/[^\s"\'<>]*property/\d+[^\s"\'<>]*',
        r'https?://(?:www\.)?thinkspain\.com/property-for-sale/\d+[^\s"\'<>]*',
        r'https?://(?:www\.)?fotocasa\.es/[^\s"\'<>]*\d+[^\s"\'<>]*',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, body):
            url = m.group(0).rstrip(">,")
            if url not in links:
                links.append(url)
    
    return {
        "id":        msg_id,
        "subject":   headers.get("Subject", ""),
        "sender":    headers.get("From", ""),
        "date":      headers.get("Date", ""),
        "body":      body,
        "snippet":   snippet,
        "links":     links,
    }

def get_last_24h_messages(service, label_id):
    """Az elmúlt 24 órában érkezett üzenetek lekérdezése"""
    # Gmail query: after:YYYY/MM/DD
    after_date = (datetime.now() - timedelta(hours=24)).strftime("%Y/%m/%d")
    query = f"after:{after_date}"
    
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=[label_id],
            q=query,
            maxResults=100
        ).execute()
        messages = result.get("messages", [])
        return messages
    except Exception as e:
        print(f"Hiba a levelek lekérdezésekor: {e}")
        return []

def parse_email_date(date_str):
    """Email dátum string → datetime objektum"""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None

# ── Ingatlan szűrési logika ───────────────────────────────────────────────────

def identify_portal(sender):
    """Az email feladója alapján portál azonosítása"""
    s = sender.lower()
    portals = ["idealista.com", "kyero.com", "thinkspain.com", "fotocasa.es"]
    for p in portals:
        if p in s:
            return p
    return "ismeretlen"

def extract_property_info(body_text):
    """Egyszerű regex alapú információk kinyerése"""
    info = {
        "price": None,
        "size": None,
        "city": None,
        "sea_distance": None,
    }
    
    # Ár keresése
    price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*€', body_text.replace(',', ''))
    if price_match:
        info["price"] = int(price_match.group(1).replace('.', ''))
    
    # Méret keresése
    size_match = re.search(r'(\d{1,4})\s*m²', body_text)
    if size_match:
        info["size"] = int(size_match.group(1))
    
    # Város keresése (egyszerűsített)
    # Spanyol városok gyakori nevei
    spanish_cities = ["malaga", "marbella", "alicante", "torrevieja", "benidorm", 
                     "valencia", "murcia", "cartagena", "bilbao", "san sebastian"]
    for city in spanish_cities:
        if city in body_text.lower():
            info["city"] = city.capitalize()
            break
    
    # Tenger távolság
    sea_match = re.search(r'(\d{1,2})\s*km.*sea|sea.*(\d{1,2})\s*km', body_text.lower())
    if sea_match:
        info["sea_distance"] = int(sea_match.group(1) or sea_match.group(2))
    
    return info

def evaluate_property(info):
    """Szűrés a megadott szempontok alapján"""
    score = 0
    reasons = []
    
    # Strand közelség (0-30 km)
    if info["sea_distance"]:
        if info["sea_distance"] <= 10:
            score += 3
            reasons.append(f"Strand közelben ({info['sea_distance']} km)")
        elif info["sea_distance"] <= 20:
            score += 2
            reasons.append(f"Strand közepes távolságra ({info['sea_distance']} km)")
        elif info["sea_distance"] <= 30:
            score += 1
            reasons.append(f"Strand 30 km-nél közelebb ({info['sea_distance']} km)")
    
    # Városközpont távolsága (bizonyos kulcsszavak alapján)
    body_lower = info.get("body_lower", "")
    if "centro" in body_lower or "city center" in body_lower or "walking distance" in body_lower:
        score += 2
        reasons.append("Városközpont közelében")
    
    # Ár (170k€ max)
    if info["price"]:
        if info["price"] <= 150000:
            score += 3
            reasons.append(f"Jó ár ({info['price']:,} €)")
        elif info["price"] <= 170000:
            score += 2
            reasons.append(f"Megfizethető ár ({info['price']:,} €)")
        elif info["price"] <= 200000:
            score += 1
            reasons.append(f"Átlagos ár ({info['price']:,} €)")
    
    # Ingatlan méret (min 100 m²)
    if info["size"]:
        if info["size"] >= 120:
            score += 3
            reasons.append(f"Nagy méret ({info['size']} m²)")
        elif info["size"] >= 100:
            score += 2
            reasons.append(f"Megfelelő méret ({info['size']} m²)")
    
    # Telek méret (kert)
    if "jardín" in body_lower or "garden" in body_lower or "terreno" in body_lower:
        score += 2
        reasons.append("Kert/telek")
    
    return score, reasons

# ── Fő funkció ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Gmail 'ingatlan' mappa ellenőrzése (elmúlt 24 óra)")
    print("=" * 60)
    
    try:
        # Gmail kapcsolat
        service = get_gmail_service()
        label_id = get_label_id(service, GMAIL_LABEL)
        
        if not label_id:
            print(f"Hiba: '{GMAIL_LABEL}' mappa nem található!")
            return
        
        # Üzenetek lekérése
        messages = get_last_24h_messages(service, label_id)
        print(f"\nTalált üzenetek: {len(messages)}")
        
        if not messages:
            print("\nNincs új ingatlan")
            return
        
        relevants = []
        
        for msg in messages:
            details = get_message_details(service, msg["id"])
            portal = identify_portal(details["sender"])
            
            print(f"\n{'-'*50}")
            print(f"Feladó: {portal}")
            print(f"Tárgy: {details['subject']}")
            print(f"Dátum: {details['date'][:25]}")
            
            # Alap információk kinyerése
            body_text = details['body'][:2000]
            info = extract_property_info(body_text)
            info["body_lower"] = body_text.lower()
            
            # Szűrés
            score, reasons = evaluate_property(info)
            
            if score >= 3:  # Minimum relevancia küszöb
                relevants.append({
                    "subject": details["subject"],
                    "sender": portal,
                    "date": details["date"],
                    "info": info,
                    "score": score,
                    "reasons": reasons,
                    "links": details["links"]
                })
                
                print(f"Pontszám: {score}/10")
                for reason in reasons:
                    print(f"  * {reason}")
                if details["links"]:
                    print(f"Linkek: {len(details['links'])} talált")
            else:
                print(f"Pontszám: {score}/10 (nem releváns)")
        
        # Összefoglaló
        print(f"\n{'='*60}")
        print(f"ÖSSZEFOGLALÓ")
        print(f"Összes üzenet: {len(messages)}")
        print(f"Releváns ingatlanok: {len(relevants)}")
        print(f"{'='*60}")
        
        if relevants:
            for i, prop in enumerate(relevants, 1):
                print(f"\n{i}. {prop['subject']}")
                print(f"   Portál: {prop['sender']}")
                print(f"   Dátum: {prop['date'][:25]}")
                if prop['info']['price']:
                    print(f"   Ár: {prop['info']['price']:,} €")
                if prop['info']['size']:
                    print(f"   Méret: {prop['info']['size']} m²")
                if prop['info']['city']:
                    print(f"   Város: {prop['info']['city']}")
                if prop['info']['sea_distance']:
                    print(f"   Tenger távolság: {prop['info']['sea_distance']} km")
                print(f"   Pontszám: {prop['score']}/10")
                print(f"   Okok: {', '.join(prop['reasons'])}")
                if prop['links']:
                    print(f"   Link: {prop['links'][0]}")
        else:
            print("\nNincs releváns ingatlan az elmúlt 24 órában")
            
    except Exception as e:
        print(f"Hiba történt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()