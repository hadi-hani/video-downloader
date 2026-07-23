from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error

# cobalt instances — server-side, no CORS, no JWT issues
INSTANCES = [
    'https://cobalt.api.timelessnesses.me',
    'https://cobalt.lem.sh',
    'https://api.cobalt.tools',
]

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except Exception:
            self._json(400, {'status': 'error', 'error': {'code': 'error.api.link.invalid'}})
            return

        video_url = payload.get('url', '').strip()
        if not video_url:
            self._json(400, {'status': 'error', 'error': {'code': 'error.api.link.invalid'}})
            return

        request_body = json.dumps({
            'url': video_url,
            'videoQuality': '1080',
            'filenameStyle': 'classic',
            'downloadMode': 'auto',
            'disableMetadata': True
        }).encode('utf-8')

        last_error = None

        for instance in INSTANCES:
            try:
                req = urllib.request.Request(
                    instance,
                    data=request_body,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                # skip this instance if it needs auth
                if data.get('status') == 'error':
                    code = ''
                    err = data.get('error', {})
                    if isinstance(err, dict):
                        code = err.get('code', '')
                    elif isinstance(err, str):
                        code = err
                    if 'auth' in code or 'jwt' in code:
                        last_error = data
                        continue

                self._json(200, data)
                return

            except urllib.error.HTTPError as e:
                try:
                    last_error = json.loads(e.read().decode('utf-8'))
                except Exception:
                    last_error = {'status': 'error', 'error': {'code': 'error.api.fetch.fail'}}
                # if auth error, try next
                continue
            except Exception as e:
                last_error = {'status': 'error', 'error': {'code': 'error.api.fetch.fail', 'message': str(e)}}
                continue

        # all instances failed
        self._json(502, last_error or {
            'status': 'error',
            'error': {'code': 'error.api.fetch.fail'}
        })

    def _json(self, code, body_dict):
        body = json.dumps(body_dict).encode('utf-8')
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
