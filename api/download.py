from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error

COBALT_API = "https://api.cobalt.tools/"

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        video_url = data.get("url", "").strip()

        if not video_url or not video_url.startswith("http"):
            self._respond(400, {"error": "من فضلك أدخل رابطاً صالحاً"})
            return

        try:
            payload = json.dumps({
                "url": video_url,
                "videoQuality": "max",
                "filenameStyle": "classic",
                "downloadMode": "auto",
                "disableMetadata": True
            }).encode("utf-8")

            req = urllib.request.Request(
                COBALT_API,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="ignore")[:300]
            self._respond(502, {"error": f"خطأ من خادم التحميل ({e.code}): {body_err}"})
            return
        except urllib.error.URLError as e:
            self._respond(503, {"error": f"تعذّر الوصول إلى خادم التحميل: {str(e.reason)}"})
            return
        except Exception as e:
            self._respond(500, {"error": f"خطأ داخلي: {str(e)[:200]}"})
            return

        status = result.get("status", "")

        if status in ("stream", "redirect", "tunnel"):
            out = {"download_url": result.get("url"), "filename": result.get("filename", "video.mp4")}
        elif status == "picker":
            picker = result.get("picker", [])
            if picker:
                out = {"download_url": picker[0].get("url"), "filename": picker[0].get("filename", "video.mp4")}
            else:
                out = {"error": "لم يتم العثور على رابط"}
        elif status == "error":
            err = result.get("error", {})
            err_text = err.get("code", "خطأ") if isinstance(err, dict) else str(err)
            out = {"error": f"فشل: {err_text}"}
        else:
            out = {"error": f"استجابة غير متوقعة: {status}"}

        self._respond(200, out)

    def _respond(self, code, body_dict):
        body = json.dumps(body_dict).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
