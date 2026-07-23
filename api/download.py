import json
import tempfile
import os
import base64
from http.server import BaseHTTPRequestHandler
import yt_dlp

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

        if not video_url:
            self._respond(400, {"error": "الرابط مطلوب"})
            return

        if not video_url.startswith('http'):
            self._respond(400, {"error": "رابط غير صالح"})
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_template = os.path.join(tmpdir, 'video.%(ext)s')

                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': output_template,
                    'merge_output_format': 'mp4',
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    ext = info.get('ext', 'mp4')

                # Find the downloaded file
                downloaded = None
                for fname in os.listdir(tmpdir):
                    if fname.startswith('video'):
                        downloaded = os.path.join(tmpdir, fname)
                        break

                if not downloaded or not os.path.exists(downloaded):
                    self._respond(500, {"error": "لم يتم إنشاء ملف الفيديو"})
                    return

                with open(downloaded, 'rb') as f:
                    video_bytes = f.read()

                b64 = base64.b64encode(video_bytes).decode('utf-8')
                download_url = f"data:video/mp4;base64,{b64}"

                self._respond(200, {"download_url": download_url, "message": "تم التحميل بنجاح"})

        except yt_dlp.utils.DownloadError as e:
            self._respond(500, {"error": f"فشل تحميل الفيديو: {str(e)[:200]}"})
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
