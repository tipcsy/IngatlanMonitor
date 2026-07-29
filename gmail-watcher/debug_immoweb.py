"""Debug: linkek kinyerése immoweb.be emailekből — miért 0 a felismert link."""
import re
import sys
sys.path.insert(0, ".")
from gmail_watcher import get_gmail_service, get_label_id, fetch_new_messages, get_message_details, extract_body

service  = get_gmail_service()
state    = {"processed_ids": []}
label_id = get_label_id(service, "Hírlevelek/Ingatlan")
messages = fetch_new_messages(service, label_id, state)

immoweb_msgs = []
for msg in messages:
    d = get_message_details(service, msg["id"])
    if "immoweb.be" in d["sender"].lower():
        immoweb_msgs.append((msg, d))

print(f"{len(immoweb_msgs)} immoweb.be email található a mappában.\n")

for msg, d in immoweb_msgs[:1]:
    full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
    html = extract_body(full["payload"])

    print(f"TÁRGY: {d['subject']}")
    print(f"BODY hossz: {len(html)} karakter")

    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
    print(f"Összes href a levélben: {len(hrefs)} db")
    for h in hrefs[:15]:
        print(f"  - {h[:200]}")

    immoweb_hits = [h for h in hrefs if "immoweb" in h.lower()]
    print(f"'immoweb' szót tartalmazó href-ek: {len(immoweb_hits)} db")
    print("─" * 70)
