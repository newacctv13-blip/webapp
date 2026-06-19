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

def kill_processes_on_ports():
    ports = [5000, 5002, 4040]
    for port in ports:
        try:
            r = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            for line in r.stdout.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=3)
                        print(f"  убит процесс на порту {port} (PID {pid})")
                    except Exception:
                        pass
        except Exception:
            pass
    time.sleep(1)

def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

def run_process(args, name, cwd=None):
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd)
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

def wait_ngrok_api(timeout=15):
    for i in range(timeout):
        time.sleep(1)
        try:
            r = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2)
            json.loads(r.read())
            return True
        except Exception:
            pass
    return False

def create_ngrok_tunnel():
    payload = json.dumps({
        "name": "admin",
        "addr": "http://localhost:5002",
        "proto": "http"
    }).encode()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:4040/api/tunnels",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        r = urllib.request.urlopen(req, timeout=5)
        data = json.loads(r.read())
        return data.get("public_url")
    except Exception:
        return None

def get_ngrok_url():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3)
        data = json.loads(r.read())
        tunnels = data.get("tunnels", [])
        if tunnels:
            return tunnels[0]["public_url"]
    except Exception:
        pass
    return None

def ensure_ngrok_tunnel():
    url = get_ngrok_url()
    if url:
        return url
    log("туннель не найден, создаю через API...")
    cleanup_old_ngrok_tunnels()
    return create_ngrok_tunnel()

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print()
    print("=" * 40)
    print("  Omnom & SweetMe — LOCAL ADMIN")
    print("=" * 40)
    print()
    log("Очистка старых процессов...")
    kill_processes_on_ports()

    print()
    print(" Cloudflare Worker: https://omnom-notify.newacctv13.workers.dev")
    print(" Заказы обрабатываются автоматически.")
    print()

    log("Установка зависимостей...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=ADMIN_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
    )

    log("Запуск Admin Panel...")
    run_process(
        [sys.executable, "app.py"],
        "admin", cwd=ADMIN_DIR,
    )
    time.sleep(3)

    log("Сброс буфера заказов (если админка была недоступна)...")
    subprocess.run(
        [sys.executable, "flush_buffer.py"],
        cwd=WORKER_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
    )

    log("Запуск relay-буфера заказов...")
    run_process(
        [sys.executable, "order_relay.py"],
        "relay", cwd=WORKER_DIR,
    )
    time.sleep(2)

    log("Запуск ngrok -> relay (порт 5002)...")
    run_process(
        ["ngrok", "http", "5002", "--log=stdout"],
        "ngrok",
    )

    ngrok_url = None
    if wait_ngrok_api(timeout=10):
        ngrok_url = ensure_ngrok_tunnel()

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
