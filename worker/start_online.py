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

ADMIN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "WebAppAdmin")

processes = []

def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

def run_process(args, name):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print()
    print(" ╔══════════════════════════════════════╗")
    print(" ║   Omnom & SweetMe — LOCAL ADMIN     ║")
    print(" ╚══════════════════════════════════════╝")
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
        "admin",
    )
    time.sleep(2)

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
