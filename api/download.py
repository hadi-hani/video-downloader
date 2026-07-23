from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error
import ssl

# Public cobalt instances — tested July 2026, no JWT required
INSTANCES = [
    'https://cobalt.api.hussien.dev',
    'https://cobalt.catvibers.me',
    'https://cbl.risewill.org',
    'https://cobalt.foss.wtf',
    'https://cobalt.privacyredirect.com',
    'https://cobalt.perish.co',
    'https://api.cobalt.tools',
    'https://cobalt.lem.sh',
    'https://cobalt.api.timelessnesses.me',
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silence default stderr logs

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
            'disableMetadata': True,
        }).encode('utf-8')

        last_error = None
        skip_codes = {'error.api.auth.jwt.missing', 'error.api.auth.jwt.invalid',
                      'error.api.auth.key.missing', 'error.api.auth.key.invalid'}

        for instance in INSTANCES:
            try:
                req = urllib.request.Request(
                    instance,
                    data=request_body,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (compatible; cobalt-client/1.0)',
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                if data.get('status') == 'error':
                    err = data.get('error', {})
                    code = err.get('code', '') if isinstance(err, dict) else str(err)
                    if code in skip_codes:
                        last_error = data
                        continue  # try next instance

                self._json(200, data)
                return

            except urllib.error.HTTPError as e:
                body_bytes = b''
                try:
                    body_bytes = e.read()
                    err_data = json.loads(body_bytes.decode('utf-8'))
                    code = ''
                    err = err_data.get('error', {})
                    if isinstance(err, dict):
                        code = err.get('code', '')
                    elif isinstance(err, str):
                        code = err
                    last_error = err_data
                    if e.code == 401 or code in skip_codes:
                        continue
                except Exception:
                    last_error = {'status': 'error', 'error': {'code': 'error.api.fetch.fail'}}
                continue

            except Exception as exc:
                last_error = {
                    'status': 'error',
                    'error': {'code': 'error.api.fetch.fail', 'message': str(exc)}
                }
                continue

        # All instances failed or required auth
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
