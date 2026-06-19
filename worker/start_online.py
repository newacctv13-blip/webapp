#!/usr/bin/env python3
"""
Omnom — локальный запуск административной панели.
Заказы в продакшене обрабатываются через Cloudflare Worker.
"""

import os
import sys
import subprocess
import signal
import time
import json
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKER_DIR = os.path.dirname(__file__)
ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "WebAppAdmin")
BUFFER_FILE = os.path.join(WORKER_DIR, "pending_orders.jsonl")

processes = []

def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

def run_process(args, name, cwd=None):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    processes.append(proc)
    return proc

def cleanup(signum=None, frame=None):
    print()
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    sys.exit(0)

def cleanup_old_ngrok_tunnels():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2)
        data = json.loads(r.read())
        for t in data.get("tunnels", []):
            uri = t["uri"]
            req = urllib.request.Request(f"http://127.0.0.1:4040{uri}", method="DELETE")
            urllib.request.urlopen(req)
    except Exception:
        pass

def wait_for_ngrok(timeout=15):
    for i in range(timeout):
        time.sleep(1)
        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
            r = urllib.request.urlopen(req, timeout=2)
            data = json.loads(r.read())
            tunnels = data.get("tunnels", [])
            if tunnels:
                url = tunnels[0]["public_url"]
                return url
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
            pass
    return None

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print()
    print("=" * 40)
    print("  Omnom & SweetMe — LOCAL ADMIN")
    print("=" * 40)
    print()
    print(" Cloudflare Worker: https://omnom-notify.newacctv13.workers.dev")
    print(" Заказы обрабатываются автоматически.")
    print()

    log("Установка зависимостей...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=ADMIN_DIR, capture_output=True, timeout=30,
    )

    log("Запуск Admin Panel...")
    run_process(
        [sys.executable, "app.py"],
        "admin", cwd=ADMIN_DIR,
    )
    time.sleep(3)

    log("Сброс буфера заказов (если админка была недоступна)...")
    subprocess.run(
        [sys.executable, "-c", f"""
import json, os, urllib.request, urllib.error
bf = {repr(BUFFER_FILE)}
if os.path.exists(bf):
    with open(bf, 'r+', encoding='utf-8') as f:
        lines = f.readlines()
        f.seek(0)
        kept = []
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                req = urllib.request.Request('http://127.0.0.1:5000/ingest', data=line.encode(), headers={{"Content-Type": "application/json"}})
                urllib.request.urlopen(req, timeout=3)
            except:
                kept.append(line + '\\n')
        f.seek(0)
        f.truncate()
        f.writelines(kept)
        print(f'Buffered orders: {{len(lines) - len(kept)}} delivered, {{len(kept)}} remaining')
"""],
        capture_output=True, text=True, timeout=10,
    )

    log("Запуск relay-буфера заказов...")
    run_process(
        [sys.executable, "order_relay.py"],
        "relay", cwd=WORKER_DIR,
    )
    time.sleep(2)

    cleanup_old_ngrok_tunnels()
    log("Запуск ngrok -> relay (порт 5002)...")
    ngrok_proc = run_process(
        ["ngrok", "http", "5002", "--log=stdout"],
        "ngrok",
    )
    time.sleep(3)

    ngrok_url = wait_for_ngrok(timeout=10)
    if ngrok_url:
        log(f"ngrok: {ngrok_url}")
        print(f"  -> ADMIN_WEBHOOK_URL: {ngrok_url}")
        print(f"  (заказы буферизуются, если админка недоступна)")
    else:
        log("⚠ ngrok не запустился. Проверьте, что он установлен.")

    print()
    log(f"Админка: http://127.0.0.1:5000")
    print()
    log("Нажми Ctrl+C для остановки")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
