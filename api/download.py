import json
import urllib.request
import urllib.error
from flask import Flask, request, jsonify

app = Flask(__name__)

COBALT_API = "https://api.cobalt.tools/"

@app.route("/api/download", methods=["POST", "OPTIONS"])
def download():
    if request.method == "OPTIONS":
        resp = app.make_default_options_response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    data = request.get_json(silent=True) or {}
    video_url = data.get("url", "").strip()

    if not video_url or not video_url.startswith("http"):
        return jsonify({"error": "من فضلك أدخل رابطاً صالحاً"}), 400

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
                "User-Agent": "Mozilla/5.0 (compatible; VideoDownloader/2.0)"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        status = result.get("status", "")

        if status in ("stream", "redirect", "tunnel"):
            response = jsonify({
                "download_url": result.get("url"),
                "filename": result.get("filename", "video.mp4")
            })
        elif status == "picker":
            picker = result.get("picker", [])
            if picker:
                response = jsonify({
                    "download_url": picker[0].get("url"),
                    "filename": picker[0].get("filename", "video.mp4")
                })
            else:
                response = jsonify({"error": "لم يتم العثور على رابط للتحميل"}), 500
        elif status == "error":
            err = result.get("error", {})
            err_text = err.get("code", "خطأ من الخادم") if isinstance(err, dict) else str(err)
            response = jsonify({"error": f"فشل التحميل: {err_text}"}), 500
        else:
            response = jsonify({"error": f"استجابة غير متوقعة: {status}"}), 500

    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="ignore")[:400]
        response = jsonify({"error": f"خطأ من خادم التحميل ({e.code}): {body_err}"}), 502
    except urllib.error.URLError as e:
        response = jsonify({"error": f"تعذّر الوصول إلى خادم التحميل: {str(e.reason)}"}), 503
    except Exception as e:
        response = jsonify({"error": f"خطأ داخلي: {str(e)[:200]}"}), 500

    if isinstance(response, tuple):
        r, code = response
    else:
        r, code = response, 200

    r.headers["Access-Control-Allow-Origin"] = "*"
    return r, code
