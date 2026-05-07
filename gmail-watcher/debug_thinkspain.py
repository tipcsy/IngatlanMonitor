"""Debug: ThinkSpain email összes linkje és a mellettük lévő szöveg."""
import sys, re, base64
sys.path.insert(0, ".")
from gmail_watcher import get_gmail_service, get_label_id, fetch_new_messages

service  = get_gmail_service()
state    = {"processed_ids": []}
label_id = get_label_id(service, "Hírlevelek/Ingatlan")
messages = fetch_new_messages(service, label_id, state)

def get_full_html(service, msg_id):
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

for msg in messages:
    full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
    headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
    sender  = headers.get("From", "")
    subject = headers.get("Subject", "")

    if "thinkspain" in sender.lower():
        print(f"TÁRGY: {subject}\n")
        html = get_full_html(service, msg["id"])

        # Keressük a property linkek + körülöttük lévő szöveget
        pattern = r'href=["\']([^"\']*thinkspain\.com/property-for-sale/\d+[^"\']*)["\'][^>]*>([^<]{0,100})'
        matches = re.findall(pattern, html)
        print(f"ThinkSpain property linkek ({len(matches)} db):")
        for url, text in matches:
            print(f"  URL: {url[:80]}")
            print(f"  Text: {text.strip()[:60]}")
            print()
        break
