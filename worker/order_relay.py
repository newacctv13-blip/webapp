import os
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BUFFER_FILE = os.path.join(os.path.dirname(__file__), "pending_orders.jsonl")
ADMIN_INGEST_URL = "http://127.0.0.1:5000/ingest"
PORT = 5002
RETRY_INTERVAL = 5


class RelayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        body_str = body.decode("utf-8")

        if not forward_to_admin(body_str):
            with open(BUFFER_FILE, "a", encoding="utf-8") as f:
                f.write(body_str + "\n")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, fmt, *args):
        print(f"[order_relay] {args[0]} {args[1]} {args[2]}")


def forward_to_admin(body: str) -> bool:
    try:
        req = Request(
            ADMIN_INGEST_URL,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urlopen(req, timeout=3)
        return True
    except (URLError, HTTPError, OSError):
        return False


def retry_loop():
    while True:
        time.sleep(RETRY_INTERVAL)
        if not os.path.exists(BUFFER_FILE):
            continue
        try:
            with open(BUFFER_FILE, "r+", encoding="utf-8") as f:
                lines = f.readlines()
                f.seek(0)
                kept = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if forward_to_admin(line):
                        print(f"[order_relay] buffered order delivered")
                    else:
                        kept.append(line + "\n")
                f.seek(0)
                f.truncate()
                f.writelines(kept)
        except Exception as e:
            print(f"[order_relay] retry error: {e}")


def main():
    threading.Thread(target=retry_loop, daemon=True).start()

    server = HTTPServer(("127.0.0.1", PORT), RelayHandler)
    print(f"[order_relay] buffer relay on http://127.0.0.1:{PORT}")
    print(f"[order_relay] forwarding to {ADMIN_INGEST_URL}")
    print(f"[order_relay] buffer: {BUFFER_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
