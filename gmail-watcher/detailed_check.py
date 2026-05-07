#!/usr/bin/env python3
"""
Részletes ingatlan szűrés az elmúlt 24 óra leveleiből a RULES.md szabályrendszer alapján
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
RULES_FILE = BASE_DIR.parent / "RULES.md"
GMAIL_LABEL = "Hírlevelek/Ingatlan"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def safe_print(text):
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
    
    # Linkek kinyerése
    links = []
    patterns = [
        r'https?://(?:www\.)?idealista\.com/(?:en/)?inmueble/\d+/[^\s"\']*',
        r'https?://(?:www\.)?kyero\.com/[^\s"\']*property/\d+[^\s"\']*',
        r'https?://(?:www\.)?thinkspain\.com/property-for-sale/\d+[^\s"\']*',
        r'https?://(?:www\.)?fotocasa\.es/[^\s"\']*\d+[^\s"\']*',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, body):
            url = m.group(0).rstrip(">,")
            if url not in links:
                links.append(url)
    
    return {
        "id": msg_id,
        "subject": headers.get("Subject", ""),
        "sender": headers.get("From", ""),
        "date": headers.get("Date", ""),
        "body": body[:5000],
        "links": links,
    }

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
        safe_print(f"Hiba a levelek lekérdezésekor: {e}")
        return []

def identify_portal(sender):
    s = sender.lower()
    portals = ["idealista.com", "kyero.com", "thinkspain.com", "fotocasa.es"]
    for p in portals:
        if p in s:
            return p
    return "ismeretlen"

def evaluate_property(email_details):
    """Egyszerű szűrés a RULES.md alapján"""
    body = email_details["body"].lower()
    subject = email_details["subject"].lower()
    portal = identify_portal(email_details["sender"])
    
    # 1. Csak spanyol portálok
    if portal == "ismeretlen":
        return 0, ["Nem spanyol portál"]
    
    # 2. Regionális szűrés
    spanish_regions = ["costa del sol", "costa blanca", "costa cálida", "valencia", "andalucia", "alicante", "malaga", "murcia"]
    region_found = any(region in body for region in spanish_regions)
    if not region_found:
        # Check for spanish city names
        spanish_cities = ["malaga", "marbella", "alicante", "torrevieja", "benidorm", "valencia", "murcia", "cartagena"]
        if not any(city in body for city in spanish_cities):
            return 0, ["Nem spanyol régió"]
    
    score = 0
    reasons = []
    
    # 3. Ár szűrés (170k€ max hitel nélkül, 320k€ max hitellel)
    price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*€', email_details["body"].replace(',', ''))
    if price_match:
        price = int(price_match.group(1).replace('.', ''))
        if price <= 170000:
            score += 3
            reasons.append(f"Megfizetheto ar ({price:,} €)")
        elif price <= 320000:
            score += 1
            reasons.append(f"Magas ar, hitel kellene ({price:,} €)")
        else:
            score -= 2
            reasons.append(f"Tul magas ar ({price:,} €)")
    else:
        reasons.append("Ar nem talalhato")
    
    # 4. Ingatlan méret (min 100 m²)
    size_match = re.search(r'(\d{1,4})\s*m²', body)
    if size_match:
        size = int(size_match.group(1))
        if size >= 120:
            score += 3
            reasons.append(f"Nagy meret ({size} m²)")
        elif size >= 100:
            score += 2
            reasons.append(f"Megfelelo meret ({size} m²)")
        else:
            score -= 1
            reasons.append(f"Kicsi meret ({size} m²)")
    else:
        reasons.append("Meret nem talalhato")
    
    # 5. Telek/kert
    if "jardín" in body or "garden" in body or "terreno" in body or "parcela" in body:
        score += 2
        reasons.append("Van kert/telek")
    elif "terraza" in body or "terrace" in body:
        score += 0.5
        reasons.append("Csak terasz (nem kert)")
    else:
        reasons.append("Kert/telek informacio hianyzik")
    
    # 6. Parkolás
    if "garaje" in body or "garage" in body or "parking" in body or "aparcamiento" in body:
        score += 2
        reasons.append("Van parkolo")
    else:
        reasons.append("Parkolas informacio hianyzik")
    
    # 7. Tenger közelség
    sea_patterns = [
        r'(\d{1,2})\s*km.*sea',
        r'(\d{1,2})\s*km.*beach',
        r'sea.*(\d{1,2})\s*km',
        r'beach.*(\d{1,2})\s*km',
        r'walking distance.*sea',
        r'walking distance.*beach'
    ]
    sea_found = False
    for pattern in sea_patterns:
        match = re.search(pattern, body)
        if match:
            sea_found = True
            try:
                km = int(match.group(1) or match.group(2) if match.groups() > 1 else 0)
                if km <= 10:
                    score += 3
                    reasons.append(f"Strand kozelben ({km} km)")
                elif km <= 20:
                    score += 2
                    reasons.append(f"Strand kozepesen ({km} km)")
                elif km <= 30:
                    score += 1
                    reasons.append(f"Strand 30 km-nel kozelebb ({km} km)")
                else:
                    reasons.append(f"Strand tul messze ({km} km)")
            except:
                score += 1
                reasons.append("Strand gyalog tavolsagra")
            break
    
    if not sea_found:
        reasons.append("Strand tavolsag informacio hianyzik")
    
    # 8. Városközpont
    if "centro" in body or "city center" in body or "walking distance" in body:
        score += 2
        reasons.append("Varoskozpont kozelben")
    
    return round(score, 1), reasons

def main():
    safe_print("=" * 60)
    safe_print("INGATLAN SZURES - Elmúlt 24 óra")
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
        
        relevant_properties = []
        
        for msg in messages:
            details = get_message_details(service, msg["id"])
            portal = identify_portal(details["sender"])
            
            # Csak spanyol portálokat nézünk
            if portal == "ismeretlen":
                continue
            
            safe_print(f"\n{'='*40}")
            safe_print(f"Portal: {portal}")
            safe_print(f"Targy: {details['subject'][:80]}")
            safe_print(f"Datum: {details['date'][:25]}")
            
            score, reasons = evaluate_property(details)
            
            if score >= 3:  # Minimum relevancia
                relevant_properties.append({
                    "subject": details["subject"],
                    "portal": portal,
                    "date": details["date"],
                    "score": score,
                    "reasons": reasons,
                    "links": details["links"]
                })
                
                safe_print(f"Pontszam: {score}/10")
                for reason in reasons[:5]:  # Max 5 ok
                    safe_print(f"  - {reason}")
                if details["links"]:
                    safe_print(f"  Linkek: {len(details['links'])}")
        
        # Összefoglaló
        safe_print(f"\n{'='*60}")
        safe_print("OSSZEFOGLALO")
        safe_print(f"Osszes uzenet: {len(messages)}")
        safe_print(f"Relevans ingatlanok: {len(relevant_properties)}")
        safe_print(f"{'='*60}")
        
        if relevant_properties:
            safe_print("\nRELEVANS INGATLANOK:")
            for i, prop in enumerate(relevant_properties, 1):
                safe_print(f"\n{i}. {prop['subject'][:60]}")
                safe_print(f"   Portal: {prop['portal']}")
                safe_print(f"   Datum: {prop['date'][:25]}")
                safe_print(f"   Pontszam: {prop['score']}/10")
                safe_print(f"   Fo okok: {', '.join(prop['reasons'][:3])}")
                if prop["links"]:
                    safe_print(f"   Link: {prop['links'][0]}")
        else:
            safe_print("\nNincs relevans ingatlan az elmult 24 oraban")
            
    except Exception as e:
        safe_print(f"Hiba tortent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()