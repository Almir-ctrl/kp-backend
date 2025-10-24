"""Minimal backend skeleton implementing the endpoints described in
BACKEND_CHANGES_FOR_FRONTEND.md

Endpoints included:
- Health: GET /health
- Upload: POST /upload (multipart/form-data, file field)
- Songs CRUD: GET /songs, GET/PATCH/DELETE /songs/<file_id>
- Process: POST /process/<model>/<file_id> (simulated background job)
- Status: GET /status/<job_id>
- Download: GET /download/<file_id>[/<artifact_key>]
- Proxy audio: POST /proxy-audio (stream remote audio)
- Cleanup: DELETE /cleanup/<file_id>

This is intentionally small and uses sqlite + filesystem for persistence.
Run: python server/backend_skeleton.py
"""

import os
import uuid
import json
import sqlite3
import threading
import time
from pathlib import Path
from flask import (  # type: ignore
    Flask,
    request,
    jsonify,
    send_file,
    Response,
    stream_with_context,
)
import requests  # type: ignore

try:
    from rq import Queue  # type: ignore
    from redis import Redis  # type: ignore
except Exception:
    Queue = None
    Redis = None

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
DB_PATH = BASE_DIR / "server" / "backend_skeleton.db"

for p in (UPLOADS_DIR, OUTPUTS_DIR, BASE_DIR / "server"):
    p.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB default limit

# Simple sqlite helper


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS songs (
            id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            filename TEXT,
            duration REAL,
            metadata TEXT,
            created_at REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            file_id TEXT,
            model TEXT,
            status TEXT,
            progress REAL,
            message TEXT,
            created_at REAL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "version": "1.0.0"})


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400
    ext = os.path.splitext(f.filename)[1] or ".bin"
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    dest = UPLOADS_DIR / filename
    f.save(str(dest))
    metadata = request.form.get("metadata")
    try:
        meta_obj = json.loads(metadata) if metadata else {}
    except Exception:
        meta_obj = {}
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        (
            "INSERT INTO songs (id, title, artist, filename, duration, "
            "metadata, created_at) VALUES (?,?,?,?,?,?,?)"
        ),
        (
            file_id,
            meta_obj.get("title"),
            meta_obj.get("artist"),
            filename,
            None,
            json.dumps(meta_obj),
            time.time(),
        ),
    )
    conn.commit()
    conn.close()
    return (
        jsonify(
            {
                "file_id": file_id,
                "url": f"/download/{file_id}",
                "title": meta_obj.get("title"),
                "artist": meta_obj.get("artist"),
            }
        ),
        201,
    )


@app.route("/songs", methods=["GET"])
def list_songs():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()
    songs = []
    for r in rows:
        obj = dict(r)
        obj["metadata"] = json.loads(r["metadata"]) if r["metadata"] else {}
        obj["url"] = f"/download/{r['id']}"
        songs.append(obj)
    conn.close()
    return jsonify({"songs": songs})


@app.route("/songs/<file_id>", methods=["GET", "PATCH", "DELETE"])
def song_detail(file_id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == "GET":
        cur.execute("SELECT * FROM songs WHERE id=?", (file_id,))
        r = cur.fetchone()
        if not r:
            return jsonify({"error": "not found"}), 404
        obj = dict(r)
        obj["metadata"] = json.loads(r["metadata"]) if r["metadata"] else {}
        obj["url"] = f"/download/{r['id']}"
        conn.close()
        return jsonify(obj)
    elif request.method == "PATCH":
        body = request.get_json() or {}
        # Support updating title, artist, lyrics/timedLyrics inside metadata
        cur.execute("SELECT metadata FROM songs WHERE id=?", (file_id,))
        r = cur.fetchone()
        if not r:
            return jsonify({"error": "not found"}), 404
        existing = json.loads(r["metadata"]) if r["metadata"] else {}
        existing.update(body)
        cur.execute(
            "UPDATE songs SET title=?, artist=?, metadata=? WHERE id=?",
            (
                body.get("title", existing.get("title")),
                body.get("artist", existing.get("artist")),
                json.dumps(existing),
                file_id,
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": file_id, **existing})
    else:  # DELETE
        cur.execute("SELECT filename FROM songs WHERE id=?", (file_id,))
        r = cur.fetchone()
        if r and r["filename"]:
            try:
                (UPLOADS_DIR / r["filename"]).unlink()
            except FileNotFoundError:
                pass
        cur.execute("DELETE FROM songs WHERE id=?", (file_id,))
        conn.commit()
        conn.close()
    return ("", 204)


# Simple background job runner


def background_process(job_id, file_id, model):
    conn = get_db()
    cur = conn.cursor()
    try:
        # simulate work
        for i in range(1, 6):
            time.sleep(1)
            cur.execute(
                "UPDATE jobs SET progress=?, message=? WHERE id=?",
                (i / 5.0, f"stage {i}", job_id),
            )
            conn.commit()

        # create a dummy output artifact (copy original if exists)
        cur.execute("SELECT filename FROM songs WHERE id=?", (file_id,))
        r = cur.fetchone()
        outputs_dir = OUTPUTS_DIR / file_id
        outputs_dir.mkdir(parents=True, exist_ok=True)
        if r and r["filename"]:
            src = UPLOADS_DIR / r["filename"]
            if src.exists():
                dest = outputs_dir / ("instrumental" + src.suffix)
                try:
                    import shutil

                    shutil.copy2(src, dest)
                except Exception:
                    pass

        cur.execute(
            "UPDATE jobs SET status=?, progress=?, message=? WHERE id=?",
            ("completed", 1.0, "done", job_id),
        )
        conn.commit()
    except Exception as e:
        cur.execute(
            "UPDATE jobs SET status=?, message=? WHERE id=?",
            ("failed", str(e), job_id),
        )
        conn.commit()
    finally:
        conn.close()


# Simple SQLite-backed poller: looks for jobs with status 'queued'
# and runs them.


def job_poller(poll_interval: float = 1.0):
    """Continuously poll the jobs table for jobs with status 'queued'

    This keeps a single background thread that serially runs jobs using the
    existing ``background_process`` function. It's intentionally simple and
    suitable for development; for production use a proper queue (RQ/Celery).
    """
    while True:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, file_id, model FROM jobs "
                "WHERE status=? ORDER BY created_at LIMIT 1",
                ("queued",),
            )
            r = cur.fetchone()
            conn.close()
            if r:
                job_id = r["id"]
                file_id = r["file_id"]
                model = r["model"]
                # mark as processing
                conn2 = get_db()
                cur2 = conn2.cursor()
                cur2.execute(
                    "UPDATE jobs SET status=?, message=? WHERE id=?",
                    ("processing", "taken by poller", job_id),
                )
                conn2.commit()
                conn2.close()
                # run job synchronously in poller thread
                try:
                    background_process(job_id, file_id, model)
                except Exception:
                    pass
            else:
                time.sleep(poll_interval)
        except Exception:
            # swallow errors and retry after a short sleep
            time.sleep(poll_interval)


# start single poller thread (daemon)

_poller_thread = threading.Thread(target=job_poller, args=(), daemon=True)
_poller_thread.start()


@app.route("/process/<model>/<file_id>", methods=["POST"])
def start_process(model, file_id):
    conn = get_db()
    cur = conn.cursor()
    job_id = str(uuid.uuid4())
    cur.execute(
        (
            "INSERT INTO jobs (id,file_id,model,status,progress,"
            "message,created_at) VALUES (?,?,?,?,?,?,?)"
        ),
        (
            job_id,
            file_id,
            model,
            "processing",
            0.0,
            "queued",
            time.time(),
        ),
    )
    conn.commit()
    conn.close()
    # If REDIS_URL is provided and rq is available, enqueue the job there.
    redis_url = os.environ.get("REDIS_URL")
    if redis_url and Queue is not None and Redis is not None:
        try:
            r = Redis.from_url(redis_url)
            q = Queue("default", connection=r)
            q.enqueue_call(
                func=background_process, args=(job_id, file_id, model)
            )
        except Exception:
            # fallback to in-process thread
            t = threading.Thread(
                target=background_process,
                args=(job_id, file_id, model),
                daemon=True,
            )
            t.start()
    else:
        # default: run in a background thread (development)
        t = threading.Thread(
            target=background_process,
            args=(job_id, file_id, model),
            daemon=True,
        )
        t.start()
        return (
            jsonify(
                {
                    "status": "accepted",
                    "job_id": job_id,
                    "file_id": file_id,
                }
            ),
            202,
        )


@app.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return jsonify({"error": "not found"}), 404
    obj = dict(r)
    return jsonify(obj)


@app.route("/download/<file_id>", methods=["GET"])
@app.route("/download/<file_id>/<artifact_key>", methods=["GET"])
def download(file_id, artifact_key=None):
    outputs_dir = OUTPUTS_DIR / file_id
    if artifact_key:
        # look for file starting with artifact_key
        if not outputs_dir.exists():
            return jsonify({"error": "not found"}), 404
        for p in outputs_dir.iterdir():
            if p.name.startswith(artifact_key):
                return send_file(str(p), as_attachment=True)
        return jsonify({"error": "artifact not found"}), 404
    else:
        # return original upload if present
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM songs WHERE id=?", (file_id,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return jsonify({"error": "not found"}), 404
        src = UPLOADS_DIR / r["filename"]
        if not src.exists():
            return jsonify({"error": "file missing"}), 404
        return send_file(str(src), as_attachment=True)


@app.route("/proxy-audio", methods=["POST"])
def proxy_audio():
    data = request.get_json() or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        r = requests.get(url, stream=True, timeout=10)
    except Exception as e:
        return jsonify({"error": f"fetch failed: {e}"}), 502

    def gen():
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    headers = {
        "Content-Type": (
            r.headers.get("Content-Type", "application/octet-stream")
        )
    }

    return Response(stream_with_context(gen()), headers=headers)


@app.route("/uploads", methods=["POST"])
def create_upload():
    """Create a resumable upload session and return an upload_id."""
    upload_id = str(uuid.uuid4())
    upload_dir = UPLOADS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    # store metadata if provided
    metadata = request.get_json() or {}
    (upload_dir / "meta.json").write_text(json.dumps(metadata))
    return jsonify({"upload_id": upload_id}), 201


@app.route("/uploads/<upload_id>/chunk", methods=["POST"])
def upload_chunk(upload_id):
    """Append a chunk to the upload.

    Client must send 'X-Chunk-Index' header (int) and a binary body.
    """
    upload_dir = UPLOADS_DIR / upload_id
    if not upload_dir.exists():
        return jsonify({"error": "upload not found"}), 404
    chunk_index = request.headers.get("X-Chunk-Index")
    if chunk_index is None:
        return jsonify({"error": "X-Chunk-Index header required"}), 400
    try:
        idx = int(chunk_index)
    except Exception:
        return jsonify({"error": "invalid chunk index"}), 400

    chunk_path = upload_dir / f"chunk-{idx:06d}.part"
    with open(chunk_path, "wb") as fh:
        fh.write(request.get_data())
    return ("", 204)


@app.route("/uploads/<upload_id>/complete", methods=["POST"])
def complete_upload(upload_id):
    """Assemble chunks in order and register final file.

    Returns JSON with file_id and download url.
    """
    upload_dir = UPLOADS_DIR / upload_id
    if not upload_dir.exists():
        return jsonify({"error": "upload not found"}), 404
    # assemble
    parts = sorted(
        [p for p in upload_dir.iterdir() if p.name.startswith("chunk-")]
    )
    if not parts:
        return jsonify({"error": "no chunks found"}), 400
    file_id = str(uuid.uuid4())
    # infer extension from metadata or default to .bin
    meta_path = upload_dir / "meta.json"
    ext = ".bin"
    if meta_path.exists():
        try:
            md = json.loads(meta_path.read_text())
            orig_name = md.get("filename")
            if orig_name:
                ext = os.path.splitext(orig_name)[1] or ext
        except Exception:
            pass
    final_name = f"{file_id}{ext}"
    final_path = UPLOADS_DIR / final_name
    with open(final_path, "wb") as out:
        for p in parts:
            with open(p, "rb") as fh:
                out.write(fh.read())
    # register as song
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        (
            "INSERT INTO songs (id, title, artist, filename, duration, "
            "metadata, created_at) VALUES (?,?,?,?,?,?,?)"
        ),
        (file_id, None, None, final_name, None, json.dumps({}), time.time()),
    )
    conn.commit()
    conn.close()
    # cleanup upload parts
    try:
        import shutil

        shutil.rmtree(upload_dir)
    except Exception:
        pass
    return jsonify({"file_id": file_id, "url": f"/download/{file_id}"}), 201


@app.route("/cleanup/<file_id>", methods=["DELETE"])
def cleanup(file_id):
    # remove outputs and optionally uploads
    outputs_dir = OUTPUTS_DIR / file_id
    try:
        if outputs_dir.exists():
            import shutil

            shutil.rmtree(outputs_dir)
        # do not delete original upload by default; frontend may call
        # DELETE /songs/:id for that
        return ("", 204)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting backend skeleton on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
