#!/usr/bin/env python3
"""Standalone static server for BillingWatch landing page.
Handles /subscribe POST locally (mirrors CF Pages Function behavior).
"""
import http.server
import socketserver
import os
import json
import sqlite3
from datetime import datetime, timezone

PORT = 8080
LANDING_DIR = os.path.join(os.path.dirname(__file__), 'landing')
DB_PATH = os.path.join(os.path.dirname(__file__), 'billingwatch.db')


def ensure_signups_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS beta_signups (
            email TEXT PRIMARY KEY,
            name TEXT,
            ts TEXT,
            ip TEXT
        )
    """)
    conn.commit()
    conn.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=LANDING_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/subscribe':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw)
                email = body.get('email', '').strip().lower()
                name = body.get('name', '').strip()
                if not email or '@' not in email:
                    self._json(400, {'ok': False, 'error': 'Valid email required.'})
                    return
                conn = sqlite3.connect(DB_PATH)
                existing = conn.execute('SELECT 1 FROM beta_signups WHERE email=?', (email,)).fetchone()
                if existing:
                    conn.close()
                    self._json(200, {'ok': True, 'message': "You're already on the list!"})
                    return
                conn.execute(
                    'INSERT INTO beta_signups (email, name, ts, ip) VALUES (?,?,?,?)',
                    (email, name or None, datetime.now(timezone.utc).isoformat(), self.client_address[0])
                )
                conn.commit()
                conn.close()
                print(f'[Signup] {email} ({name})')
                self._json(200, {'ok': True, 'message': "You're on the list! We'll reach out soon."})
            except Exception as e:
                print(f'[Signup Error] {e}')
                self._json(500, {'ok': False, 'error': 'Something went wrong. Try again.'})
        else:
            self.send_error(404)

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress access logs


if __name__ == '__main__':
    ensure_signups_table()
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f'[BillingWatch Landing] Serving on http://127.0.0.1:{PORT}')
        httpd.serve_forever()
