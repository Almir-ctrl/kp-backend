# server/proxy_audio.py
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Allow all origins for local dev. Restrict in production!
CORS(app, resources={r"/*": {"origins": "*"}})

# If running behind a reverse proxy, use ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app)


@app.route("/proxy-audio", methods=["POST", "OPTIONS"])
def proxy_audio():
    # flask-cors makes OPTIONS handling easy; but we still return a simple response for OPTIONS.
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.get_json(force=True, silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    url = data["url"]
    try:
        # Stream the remote response to the client
        upstream = requests.get(url, stream=True, timeout=15)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch remote URL: {str(e)}"}), 502

    if upstream.status_code != 200:
        return (
            jsonify({"error": f"Upstream returned {upstream.status_code}"}),
            502,
        )

    # Build a streaming response, copying content-type and length when available
    headers = {}
    if upstream.headers.get("content-type"):
        headers["Content-Type"] = upstream.headers.get("content-type")
    if upstream.headers.get("content-length"):
        headers["Content-Length"] = upstream.headers.get("content-length")
    # Allow cross-origin from the dev server
    headers["Access-Control-Allow-Origin"] = "*"
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    headers["Access-Control-Allow-Headers"] = "Content-Type"

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(generate(), headers=headers, status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
