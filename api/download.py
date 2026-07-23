import json
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error

COBALT_API = "https://cobalt.tools/api/json"

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            video_url = data.get('url', '').strip()
        except Exception:
            self._respond(400, {"error": "طلب غير صالح"})
            return

        if not video_url or not video_url.startswith('http'):
            self._respond(400, {"error": "من فضلك أدخل رابطاً صالحاً"})
            return

        try:
            payload = json.dumps({
                "url": video_url,
                "vQuality": "max",
                "filenamePattern": "classic",
                "isAudioOnly": False,
                "disableMetadata": True
            }).encode('utf-8')

            req = urllib.request.Request(
                COBALT_API,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))

            status = result.get("status", "")

            if status in ("stream", "redirect", "tunnel"):
                self._respond(200, {
                    "download_url": result.get("url"),
                    "filename": result.get("filename", "video.mp4")
                })
            elif status == "picker":
                picker = result.get("picker", [])
                if picker:
                    self._respond(200, {
                        "download_url": picker[0].get("url"),
                        "filename": "video.mp4"
                    })
                else:
                    self._respond(500, {"error": "لم يتم العثور على رابط للتحميل"})
            elif status == "error":
                err_text = result.get("text", "خطأ من الخادم")
                self._respond(500, {"error": f"فشل: {err_text}"})
            else:
                self._respond(500, {"error": f"استجابة غير متوقعة: {status}"})

        except urllib.error.HTTPError as e:
            body_err = e.read().decode('utf-8', errors='ignore')[:300]
            self._respond(502, {"error": f"HTTP {e.code}: {body_err}"})
        except urllib.error.URLError as e:
            self._respond(503, {"error": f"تعذّر الوصول إلى خادم التحميل: {str(e.reason)}"})
        except Exception as e:
            self._respond(500, {"error": f"خطأ داخلي: {str(e)[:200]}"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, status, body_dict):
        body = json.dumps(body_dict, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
