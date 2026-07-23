# This file is intentionally left as a no-op stub.
# The app is now fully client-side — the browser calls cobalt instances directly.
# No server proxy needed.
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.dumps({'status':'error','error':{'code':'deprecated'}}).encode()
        self.send_response(410)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
