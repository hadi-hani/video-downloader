# This file is kept as a placeholder.
# All download logic now runs in the browser (index.html).
# The frontend calls api.cobalt.tools directly via JavaScript.
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond(200, {"status": "ok", "message": "Frontend handles downloads directly."})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def _respond(self, code, body_dict):
        body = json.dumps(body_dict).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)
