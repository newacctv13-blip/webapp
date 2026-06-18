#!/usr/bin/env python3
"""
Omnom — автоматический запуск handler + ngrok + обновление GitHub.
Запускает всё одной командой, сам обновляет data.json на GitHub Pages.
"""

import os
import sys
import json
import time
import base64
import subprocess
import threading
import signal
import webbrowser
from http.client import HTTPConnection
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

NGROK_AUTHTOKEN = "3FIgDteWuRUj0QV8WQ99mw4w7VC_2VmE1p1fFm9wKB5VaHwto"
BOT_TOKEN = "8518399300:AAEX-pbC-s2x7iId8x4-6jKqdBjdBKD9aTs"
ADMIN_CHAT_ID = "330619718"
REPO = "newacctv13-blip/webapp"
BRANCH = "gh-pages"
DATA_FILE = "data.json"
HANDLER_PORT = 8765

processes = []

def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

def run_process(args, name):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    processes.append(proc)
    return proc

def wait_for_ngrok(timeout=15):
    for i in range(timeout):
        try:
            conn = HTTPConnection("127.0.0.1", 4040, timeout=2)
            conn.request("GET", "/api/tunnels")
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            for t in data.get("tunnels", []):
                if t.get("public_url", "").startswith("https://"):
                    return t["public_url"]
        except Exception:
            pass
        time.sleep(1)
    return None

def get_github_token():
    env_token = os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def update_github_file(token, public_url):
    worker_url = f"{public_url}/notify"
    api_url = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "omnom-start-script",
    }

    req = Request(api_url, headers=headers, method="GET")
    try:
        resp = urlopen(req)
        current = json.loads(resp.read())
        current_content = base64.b64decode(current["content"]).decode("utf-8")
        sha = current["sha"]
    except HTTPError as e:
        log(f"Ошибка получения файла: {e.code} {e.read().decode()}")
        return False
    except URLError as e:
        log(f"Ошибка сети: {e.reason}")
        return False

    data = json.loads(current_content)
    data.setdefault("settings", {})["orderWorkerUrl"] = worker_url
    new_content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    payload = json.dumps({
        "message": f"auto: update worker url to {worker_url}",
        "content": encoded,
        "sha": sha,
        "branch": BRANCH,
    }).encode()

    req = Request(api_url, data=payload, headers=headers, method="PUT")
    try:
        resp = urlopen(req)
        result = json.loads(resp.read())
        log(f"data.json обновлён! Commit: {result['content']['sha'][:7]}")
        return True
    except HTTPError as e:
        log(f"Ошибка обновления: {e.code} {e.read().decode()}")
        return False
    except URLError as e:
        log(f"Ошибка сети: {e.reason}")
        return False

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

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print()
    print(" ╔══════════════════════════════════════╗")
    print(" ║   Omnom & SweetMe — ONLINE START    ║")
    print(" ╚══════════════════════════════════════╝")
    print()

    log("Авторизация ngrok...")
    subprocess.run(["ngrok", "authtoken", NGROK_AUTHTOKEN],
                   capture_output=True, timeout=10)

    log("Запуск Telegram handler...")
    env = os.environ.copy()
    env["BOT_TOKEN"] = BOT_TOKEN
    env["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID
    run_process(
        [sys.executable, "telegram_handler.py"],
        "handler"
    )
    time.sleep(2)

    log("Запуск ngrok...")
    run_process(["ngrok", "http", str(HANDLER_PORT)], "ngrok")
    time.sleep(3)

    log("Получение публичного URL...")
    public_url = wait_for_ngrok()
    if not public_url:
        log("НЕ УДАЛОСЬ получить URL от ngrok!")
        log("Проверь: ngrok установлен? Токен правильный?")
        cleanup()
        return

    log(f"ngrok URL: {public_url}")
    print()

    token = get_github_token()
    if token:
        log("Обновление data.json на GitHub Pages...")
        if update_github_file(token, public_url):
            site_url = f"https://{REPO}/{'' if REPO.endswith('.github.io') else REPO.split('/')[1]}"
            log(f"Сайт обновлён! Открой на телефоне:")
            print(f"\n   >>> {site_url} <<<\n")
        else:
            log("Не удалось обновить GitHub. Используй параметр:")
            print(f"\n   >>> {public_url.replace('https://', 'https://newacctv13-blip.github.io/webapp/?worker=')} <<<\n")
    else:
        log("GITHUB_TOKEN не найден. Используй параметр вручную:")
        print(f"\n   >>> {public_url.replace('https://', 'https://newacctv13-blip.github.io/webapp/?worker=')} <<<\n")
        print("  (установи GITHUB_TOKEN для автобновления)")

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
