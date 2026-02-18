#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os

OUTPUT = "/var/www/html/index.html"
SCRIPT = "/home/pi/pymmog.com/update_status.py"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        subprocess.run(["python3", SCRIPT], timeout=10)
        with open(OUTPUT, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass  # suppress access logs

HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
