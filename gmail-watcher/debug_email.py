"""Debug: linkek és plain text kinyerése idealista emailekből."""
import sys
sys.path.insert(0, ".")
from gmail_watcher import get_gmail_service, get_label_id, fetch_new_messages, get_message_details

service  = get_gmail_service()
state    = {"processed_ids": []}
label_id = get_label_id(service, "Hírlevelek/Ingatlan")
messages = fetch_new_messages(service, label_id, state)

for msg in messages[:8]:
    d = get_message_details(service, msg["id"])
    if "noresponder@idealista.com" in d["sender"]:
        print(f"\nTÁRGY: {d['subject']}")
        print(f"LINK:  {d['link'] or '(nem találtuk)'}")
        print(f"BODY (első 300 kar): {d['body'][:300]}")
        print("─"*60)
