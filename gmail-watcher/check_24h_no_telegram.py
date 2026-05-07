#!/usr/bin/env python3
"""
Ellenőrzés az elmúlt 24 óra 'ingatlan' leveleire, Telegram értesítés nélkül
"""

import os
import json
import base64
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Konfiguráció ──────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent
CLIENT_SECRET = BASE_DIR / "client_secret.json"
STATE_FILE    = BASE_DIR / "state.json"
RULES_FILE    = BASE_DIR.parent / "RULES.md"

GMAIL_LABEL = "Hírlevelek/Ingatlan"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ── Auth ──────────────────────────────────────────────────────────────────────

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
            maxResults=100
        ).execute()
        return result.get("messages", [])
    except Exception as e:
        print(f"[Hiba] Levelek lekérdezése: {e}")
        return []

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
    
    # Ingatlan linkek keresése
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
        "body": body,
        "links": links,
    }

def identify_portal(sender):
    s = sender.lower()
    portals = ["idealista.com", "kyero.com", "thinkspain.com", "fotocasa.es"]
    for p in portals:
        if p in s:
            return p
    return "ismeretlen"

def extract_basic_info(body_text):
    """Alapvető információk kinyerése az emailből"""
    info = {
        "prices": [],
        "sizes": [],
        "locations": [],
        "has_garden": False,
        "has_parking": False,
        "sea_distance": None,
    }
    
    # Árak keresése
    price_matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})*)\s*€', body_text.replace(',', ''))
    for price_str in price_matches:
        try:
            price = int(price_str.replace('.', ''))
            if price > 10000:  # Valószínűleg ingatlan ár
                info["prices"].append(price)
        except:
            pass
    
    # Méretek keresése
    size_matches = re.findall(r'(\d{1,4})\s*m²', body_text, re.IGNORECASE)
    for size_str in size_matches:
        try:
            size = int(size_str)
            info["sizes"].append(size)
        except:
            pass
    
    # Spanyol városok/régiók
    spanish_locations = [
        "malaga", "marbella", "alicante", "torrevieja", "benidorm", 
        "valencia", "murcia", "cartagena", "bilbao", "san sebastian",
        "costa del sol", "costa blanca", "costa cálida", "andalucia"
    ]
    for loc in spanish_locations:
        if loc in body_text.lower():
            info["locations"].append(loc.capitalize())
    
    # Kert/telek
    garden_keywords = ["jardín", "garden", "terreno", "parcela", "huerto"]
    if any(keyword in body_text.lower() for keyword in garden_keywords):
        info["has_garden"] = True
    
    # Parkolás
    parking_keywords = ["garaje", "garage", "parking", "aparcamiento", "estacionamiento"]
    if any(keyword in body_text.lower() for keyword in parking_keywords):
        info["has_parking"] = True
    
    # Tenger távolság
    sea_patterns = [
        r'(\d{1,2})\s*km.*sea',
        r'(\d{1,2})\s*km.*beach',
        r'sea.*(\d{1,2})\s*km',
        r'beach.*(\d{1,2})\s*km'
    ]
    for pattern in sea_patterns:
        match = re.search(pattern, body_text.lower())
        if match:
            try:
                info["sea_distance"] = int(match.group(1) or match.group(2))
                break
            except:
                pass
    
    return info

def evaluate_property(info, portal):
    """Értékelés a RULES.md szempontjai alapján"""
    score = 0
    reasons = []
    
    # 1. Ár (170k€ max hitel nélkül, 320k€ max hitellel)
    if info["prices"]:
        min_price = min(info["prices"])
        if min_price <= 170000:
            score += 3
            reasons.append(f"Megfizethető ár ({min_price:,} €)")
        elif min_price <= 320000:
            score += 1
            reasons.append(f"Magas ár, hitel kellene ({min_price:,} €)")
        else:
            reasons.append(f"Túl magas ár ({min_price:,} €)")
    else:
        reasons.append("Ár információ hiányzik")
    
    # 2. Méret (min 100 m²)
    if info["sizes"]:
        max_size = max(info["sizes"])
        if max_size >= 120:
            score += 3
            reasons.append(f"Nagy méret ({max_size} m²)")
        elif max_size >= 100:
            score += 2
            reasons.append(f"Megfelelő méret ({max_size} m²)")
        else:
            reasons.append(f"Kicsi méret ({max_size} m²)")
    else:
        reasons.append("Méret információ hiányzik")
    
    # 3. Kert/telek
    if info["has_garden"]:
        score += 2
        reasons.append("Van kert/telek")
    else:
        reasons.append("Kert/telek információ hiányzik")
    
    # 4. Parkolás
    if info["has_parking"]:
        score += 2
        reasons.append("Van parkoló")
    else:
        reasons.append("Parkolás információ hiányzik")
    
    # 5. Tenger távolság
    if info["sea_distance"] is not None:
        if info["sea_distance"] <= 10:
            score += 3
            reasons.append(f"Strand közelség ({info['sea_distance']} km)")
        elif info["sea_distance"] <= 20:
            score += 2
            reasons.append(f"Strand közepes távolság ({info['sea_distance']} km)")
        elif info["sea_distance"] <= 30:
            score += 1
            reasons.append(f"Strand 30 km-nél közelebb ({info['sea_distance']} km)")
        else:
            reasons.append(f"Strand túl messze ({info['sea_distance']} km)")
    else:
        reasons.append("Strand távolság információ hiányzik")
    
    # 6. Spanyol régió
    if info["locations"]:
        score += 1
        reasons.append(f"Spanyol régió: {', '.join(info['locations'][:2])}")
    else:
        reasons.append("Helyszín információ hiányzik")
    
    # 7. Portál minősítése
    if portal in ["idealista.com", "kyero.com", "thinkspain.com"]:
        score += 1
        reasons.append(f"Megbízható portál: {portal}")
    
    return min(score, 10), reasons

def main():
    print("=" * 80)
    print("INGATLAN ELLENŐRZÉS - Elmúlt 24 óra")
    print("=" * 80)
    
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
        
        relevant_properties = []
        
        for msg in messages:
            details = get_message_details(service, msg["id"])
            portal = identify_portal(details["sender"])
            
            # Csak ismert spanyol portálokat nézünk
            if portal == "ismeretlen":
                continue
            
            print(f"\n{'─'*60}")
            print(f"Portál: {portal}")
            print(f"Tárgy: {details['subject']}")
            print(f"Dátum: {details['date'][:25]}")
            
            # Alap információk kinyerése
            info = extract_basic_info(details["body"])
            
            # Értékelés
            score, reasons = evaluate_property(info, portal)
            
            if score >= 4:  # Minimum relevancia küszöb
                property_data = {
                    "subject": details["subject"],
                    "portal": portal,
                    "date": details["date"],
                    "info": info,
                    "score": score,
                    "reasons": reasons,
                    "links": details["links"][:3] if details["links"] else []
                }
                relevant_properties.append(property_data)
                
                print(f"Pontszám: {score}/10")
                print(f"Linkek: {len(details['links'])}")
                for reason in reasons[:4]:  # Legfeljebb 4 ok
                    print(f"  - {reason}")
            else:
                print(f"Pontszám: {score}/10 (nem releváns)")
        
        # Összefoglaló
        print(f"\n{'='*80}")
        print("ÖSSZEFOGLALÓ")
        print(f"{'='*80}")
        print(f"Összes üzenet: {len(messages)}")
        print(f"Spanyol portálok: {len([m for m in messages if identify_portal(get_message_details(service, m['id'])['sender']) != 'ismeretlen'])}")
        print(f"Releváns ingatlanok: {len(relevant_properties)}")
        print(f"{'='*80}")
        
        if relevant_properties:
            print("\nRELEVÁNS INGATLANOK:")
            print(f"{'─'*80}")
            
            for i, prop in enumerate(relevant_properties, 1):
                print(f"\n{i}. {prop['subject'][:70]}")
                print(f"   Portál: {prop['portal']}")
                print(f"   Dátum: {prop['date'][:25]}")
                print(f"   Pontszám: {prop['score']}/10")
                
                if prop["info"]["prices"]:
                    print(f"   Ár: {min(prop['info']['prices']):,} €")
                if prop["info"]["sizes"]:
                    print(f"   Méret: {max(prop['info']['sizes'])} m²")
                if prop["info"]["locations"]:
                    print(f"   Helyszín: {', '.join(prop['info']['locations'][:2])}")
                if prop["info"]["sea_distance"]:
                    print(f"   Tenger távolság: {prop['info']['sea_distance']} km")
                
                print(f"   Fő okok: {', '.join(prop['reasons'][:3])}")
                
                if prop["links"]:
                    print(f"   Link: {prop['links'][0][:80]}")
        else:
            print("\nNincs releváns ingatlan az elmúlt 24 órában")
            
    except Exception as e:
        print(f"Hiba történt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # A kimenet karakterkódolási problémáinak elkerülése
    import sys
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    main()