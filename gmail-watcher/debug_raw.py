"""Debug: nyers href linkek kinyerése egy idealista emailből."""
import sys, re, base64
sys.path.insert(0, ".")
from gmail_watcher import get_gmail_service, get_label_id, fetch_new_messages

service  = get_gmail_service()
state    = {"processed_ids": []}
label_id = get_label_id(service, "Hírlevelek/Ingatlan")
messages = fetch_new_messages(service, label_id, state)

def get_full_body(service, msg_id):
    """Teljes body lekérése, limit nélkül, minden part-ból."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    parts = []
    def walk(payload):
        if "parts" in payload:
            for p in payload["parts"]:
                walk(p)
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace"))
    walk(msg["payload"])
    return "\n".join(parts)

# Első idealista "new ... in your search" email
for msg in messages:
    full_msg = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
    headers = {h["name"]: h["value"] for h in full_msg["payload"].get("headers", [])}
    sender  = headers.get("From", "")
    subject = headers.get("Subject", "")

    if "noresponder@idealista.com" in sender and "new" in subject.lower():
        print(f"TÁRGY: {subject}")
        body = get_full_body(service, msg["id"])
        print(f"TELJES BODY HOSSZA: {len(body)} karakter")

        # Összes href kinyerése
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', body)
        print(f"\nÖSSZES HREF ({len(hrefs)} db):")
        for h in hrefs:
            print(f"  {h}")
        break
