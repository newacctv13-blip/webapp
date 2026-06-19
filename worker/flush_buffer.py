"""
Startup buffer flush — forwards any pending orders that accumulated
while the admin panel was down.
"""
import json
import os
import urllib.request
import urllib.error

BUFFER_FILE = os.path.join(os.path.dirname(__file__), "pending_orders.jsonl")
ADMIN_INGEST_URL = "http://127.0.0.1:5000/ingest"

if not os.path.exists(BUFFER_FILE):
    print("No buffer file")
    exit(0)

with open(BUFFER_FILE, "r+", encoding="utf-8") as f:
    lines = f.readlines()
    f.seek(0)
    kept = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            req = urllib.request.Request(
                ADMIN_INGEST_URL,
                data=line.encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            kept.append(line + "\n")
    f.seek(0)
    f.truncate()
    f.writelines(kept)

delivered = len(lines) - len(kept)
print(f"Buffered orders: {delivered} delivered, {len(kept)} remaining")
