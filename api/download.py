from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error

# Cobalt.tools public API - v1
COBALT_API = "https://api.cobalt.tools"

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
                "videoQuality": "1080",
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
                    "User-Agent": "Mozilla/5.0 (compatible; cobalt-client/1.0)",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=25) as resp:
                result = json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            try:
                body_err = e.read().decode("utf-8", errors="ignore")[:500]
                err_json = json.loads(body_err)
                err_text = err_json.get("error", {}).get("code", body_err) if isinstance(err_json.get("error"), dict) else body_err
            except Exception:
                err_text = f"HTTP {e.code}"
            self._respond(502, {"error": f"خطأ من خادم التحميل: {err_text}"})
            return
        except urllib.error.URLError as e:
            self._respond(503, {"error": f"تعذّر الوصول إلى خادم التحميل: {str(e.reason)}"})
            return
        except Exception as e:
            self._respond(500, {"error": f"خطأ داخلي: {str(e)[:300]}"})
            return

        status = result.get("status", "")

        if status in ("stream", "redirect", "tunnel"):
            out = {
                "download_url": result.get("url"),
                "filename": result.get("filename", "video.mp4")
            }
        elif status == "picker":
            picker = result.get("picker", [])
            if picker:
                first = picker[0]
                out = {
                    "download_url": first.get("url"),
                    "filename": first.get("filename", "video.mp4")
                }
            else:
                out = {"error": "لم يتم العثور على رابط تحميل"}
        elif status == "error":
            err = result.get("error", {})
            err_code = err.get("code", "unknown") if isinstance(err, dict) else str(err)
            # Friendly error messages in Arabic
            friendly = {
                "error.api.auth.key.missing": "مطلوب مفتاح API",
                "error.api.link.invalid": "الرابط غير صالح أو غير مدعوم",
                "error.api.fetch.fail": "تعذّر جلب الفيديو - قد يكون خاصاً أو محذوفاً",
                "error.api.youtube.login": "يتطلب هذا الفيديو تسجيل دخول على YouTube",
                "error.api.content.too_long": "الفيديو طويل جداً",
                "error.api.content.video.unavailable": "الفيديو غير متاح",
            }
            out = {"error": friendly.get(err_code, f"فشل التحميل: {err_code}")}
        else:
            out = {"error": f"استجابة غير متوقعة من الخادم: {json.dumps(result)[:200]}"}

        self._respond(200, out)

    def _respond(self, code, body_dict):
        body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
