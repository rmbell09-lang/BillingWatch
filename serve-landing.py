#!/usr/bin/env python3
"""Standalone static server for BillingWatch landing page."""
import http.server
import socketserver
import os

PORT = 8080
LANDING_DIR = os.path.join(os.path.dirname(__file__), 'landing')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=LANDING_DIR, **kwargs)
    def log_message(self, format, *args):
        pass  # Suppress access logs

if __name__ == '__main__':
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f'[BillingWatch Landing] Serving on http://127.0.0.1:{PORT}')
        httpd.serve_forever()
