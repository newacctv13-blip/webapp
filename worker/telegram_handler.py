#!/usr/bin/env python3
"""
Omnom & SweetMe — Local Telegram Order Handler
HTTP-сервер для приёма заказов и отправки в Telegram.
Запуск: python telegram_handler.py
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime

BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
PORT = int(os.environ.get('PORT', 8765))

ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:4173',
    'http://127.0.0.1:5173',
    'https://newacctv13-blip.github.io',
]


def escape_html(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def format_order_message(order):
    name = order.get('name', '')
    phone = order.get('phone', '')
    items = order.get('items', [])
    subtotal = order.get('subtotal', 0)
    delivery = order.get('delivery', 0)
    total = order.get('total', 0)
    currency = order.get('currency', 'L')

    lines = [
        '\U0001f36a <b>Новый заказ!</b>',
        '',
        f'\U0001f464 <b>Имя:</b> {escape_html(name)}',
        f'\U0001f4de <b>Телефон:</b> {escape_html(phone)}',
        '\U0001f4cd <b>Город:</b> Chi\u0219in\u0103u',
        '',
        '\U0001f4e6 <b>Состав заказа:</b>',
    ]

    for item in items:
        item_total = item.get('price', 0) * item.get('qty', 0)
        lines.append(
            f'  \u2022 {escape_html(item.get("name", ""))}'
            f' \u00d7 {item.get("qty", 0)} = {item_total} {currency}'
        )

    lines.extend([
        '',
        f'\U0001f4b0 <b>Сумма:</b> {subtotal} {currency}',
        f'\U0001f69a <b>Доставка:</b> {delivery} {currency}',
        f'\U0001f4b5 <b>К оплате:</b> <b>{total} {currency}</b>',
        '',
        f'\U0001f550 {datetime.now().strftime("%d.%m.%Y %H:%M")}',
    ])

    return '\n'.join(lines)


def send_telegram(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = json.dumps({
        'chat_id': ADMIN_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
    }).encode()

    req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urlopen(req)
        return True, None
    except HTTPError as e:
        body = e.read().decode() if hasattr(e, 'read') else str(e)
        return False, f'Telegram API error {e.code}: {body}'
    except URLError as e:
        return False, f'Telegram connection error: {e.reason}'


class OrderHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        origin = self.headers.get('Origin', '')
        self._send_cors(origin)
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get('Origin', '')

        if self.path != '/notify':
            self._json_response({'error': 'Not found'}, 404, origin)
            return

        if not BOT_TOKEN or not ADMIN_CHAT_ID:
            self._json_response(
                {'error': 'Worker not configured'}, 500, origin
            )
            return

        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)

        try:
            order = json.loads(body)
        except json.JSONDecodeError:
            self._json_response({'error': 'Invalid JSON'}, 400, origin)
            return

        if (
            not order.get('name')
            or not order.get('phone')
            or not isinstance(order.get('items'), list)
            or len(order['items']) == 0
        ):
            self._json_response(
                {'error': 'Missing required fields'}, 400, origin
            )
            return

        try:
            message = format_order_message(order)
            ok, err = send_telegram(message)
            if ok:
                self._json_response({'ok': True}, 200, origin)
            else:
                self._json_response({'ok': False, 'error': err}, 502, origin)
        except Exception as e:
            self._json_response({'ok': False, 'error': str(e)}, 502, origin)

    def _send_cors(self, origin):
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json_response(self, data, status, origin):
        self.send_response(status)
        self._send_cors(origin)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] {args[0]} {args[1]} {args[2]}')


def main():
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print('Ошибка: задайте BOT_TOKEN и ADMIN_CHAT_ID')
        print()
        print('  set BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
        print('  set ADMIN_CHAT_ID=123456789')
        print(f'  python {os.path.basename(__file__)}')
        print()
        sys.exit(1)

    server = HTTPServer(('127.0.0.1', PORT), OrderHandler)
    bot_short = BOT_TOKEN.split(':')[0] if ':' in BOT_TOKEN else ''
    print(f'Telegram handler запущен на http://127.0.0.1:{PORT}/notify')
    print(f'Bot ID: {bot_short}')
    print('Нажмите Ctrl+C для остановки')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nОстановлен')
        server.server_close()


if __name__ == '__main__':
    main()
