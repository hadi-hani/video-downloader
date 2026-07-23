import json
import urllib.request
import urllib.error

COBALT_API = "https://api.cobalt.tools/"

def handler(request):
    # CORS preflight
    if request.method == "OPTIONS":
        return Response(
            "",
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    if request.method != "POST":
        return Response(
            json.dumps({"error": "Method not allowed"}),
            status=405,
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        )

    try:
        body = request.body
        if isinstance(body, (bytes, bytearray)):
            data = json.loads(body.decode("utf-8"))
        else:
            data = json.loads(body)
    except Exception:
        data = {}

    video_url = data.get("url", "").strip()

    if not video_url or not video_url.startswith("http"):
        return Response(
            json.dumps({"error": "من فضلك أدخل رابطاً صالحاً"}),
            status=400,
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        )

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
        body_err = e.read().decode("utf-8", errors="ignore")[:400]
        return Response(
            json.dumps({"error": f"خطأ من خادم التحميل ({e.code}): {body_err}"}),
            status=502,
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        )
    except urllib.error.URLError as e:
        return Response(
            json.dumps({"error": f"تعذّر الوصول إلى خادم التحميل: {str(e.reason)}"}),
            status=503,
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        return Response(
            json.dumps({"error": f"خطأ داخلي: {str(e)[:200]}"}),
            status=500,
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        )

    status = result.get("status", "")

    if status in ("stream", "redirect", "tunnel"):
        out = {"download_url": result.get("url"), "filename": result.get("filename", "video.mp4")}
    elif status == "picker":
        picker = result.get("picker", [])
        if picker:
            out = {"download_url": picker[0].get("url"), "filename": picker[0].get("filename", "video.mp4")}
        else:
            out = {"error": "لم يتم العثور على رابط للتحميل"}
    elif status == "error":
        err = result.get("error", {})
        err_text = err.get("code", "خطأ من الخادم") if isinstance(err, dict) else str(err)
        out = {"error": f"فشل التحميل: {err_text}"}
    else:
        out = {"error": f"استجابة غير متوقعة: {status}"}

    return Response(
        json.dumps(out),
        status=200,
        headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
    )
