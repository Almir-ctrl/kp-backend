import os
import subprocess
import uuid
import shutil
import base64
import numpy as np
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask import Flask, request, jsonify, send_file
from flask import g
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
import whisper
from config import Config
from models import get_processor
from librosa_chroma_analyzer import EnhancedChromaAnalyzer
import soundfile as sf

# Defer heavy 'transformers' imports to runtime where needed to avoid
# blocking startup. Heavy model libraries are imported lazily below.
import logging
import datetime
import traceback
import json
# Module-level logger for non-request logging
_logger = logging.getLogger(__name__)
# RotatingFileHandler intentionally not used here; keep logging simple.


# Ensure whisper model helper (testable, lightweight)
try:
    from server.scripts.download_whisper_model import (
        ensure_model as ensure_whisper_model,
    )
except Exception:
    # Defer import errors to runtime logging below. Keep startup resilient
    # if the helper is missing.
    ensure_whisper_model = None

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-key-change-in-prod"
)

# Check GPU availability on startup
try:
    import torch

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = (
            torch.cuda.get_device_properties(0).total_memory / 1024**3
        )
        compute_capability = torch.cuda.get_device_capability(0)

        print("\n" + "=" * 60)
        print("🎮 GPU DETECTED: %s" % gpu_name)
        print("💾 GPU Memory: %.1f GB" % gpu_memory)
        # Use torch.version.cuda if available, else fall back
        cuda_version = getattr(torch.version, "cuda", torch.__version__)
        print("✅ CUDA Version: %s" % cuda_version)
        compute_str = f"sm_{compute_capability[0]}{compute_capability[1]}"
        print("🔧 Compute Capability: %s" % compute_str)
        print("🚀 PyTorch Nightly: All models using GPU acceleration")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: No GPU detected - using CPU")
        print(
            "💡 To enable GPU: pip install torch --index-url "
            "https://download.pytorch.org/whl/cu124"
        )
        print("=" * 60 + "\n")
except Exception as e:
    print("GPU check failed: %s" % str(e))


# Configure CORS for production - allow all origins including Google AI Studio
CORS(
    app,
    origins="*",
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    supports_credentials=False,
)

# Initialize SocketIO with CORS support
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# Initialize config to create directories
config = Config()

# Optionally ensure the Whisper model exists on startup. This runs in a
# background thread to avoid blocking the main server process if a
# downloader is slow.
try:
    ENSURE = (
        os.environ.get("ENSURE_WHISPER_ON_STARTUP", "true").lower() == "true"
    )
except Exception:
    ENSURE = True

if ENSURE and callable(ensure_whisper_model):
    import threading

    # Start a background thread to ensure Whisper model exists locally.
    def _ensure_whisper_bg():
        try:
            model_name = (
                app.config
                .get("MODELS", {})
                .get("whisper", {})
                .get("default_model", "medium")
            )
            if ensure_whisper_model:
                ensure_whisper_model(model_name)
                extra_log = {"request_id": "startup"}
                app.logger.info(
                    "Whisper model ensured on startup",
                    extra=extra_log,
                )
        except Exception:
            app.logger.exception("Failed to ensure Whisper model on startup")

    t = threading.Thread(
        target=_ensure_whisper_bg, name="ensure-whisper-thread", daemon=True
    )
    t.start()


@app.before_request
def log_request_info():
    """Attach a request_id to each request and log a short message."""
    try:
        incoming_req_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("x-request-id")
        )
    except Exception:
        incoming_req_id = None

    # Store request id in flask.g (avoid mutating Request object)
    g.request_id = incoming_req_id or str(uuid.uuid4())
    try:
        extra_log = {"request_id": g.request_id}
        app.logger.info(
            "Request: %s %s from %s",
            request.method,
            request.path,
            request.remote_addr,
            extra=extra_log,
        )
    except Exception:
        # Best-effort logging; do not fail the request
        pass


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    # Return JSON for HTTPExceptions (e.g., 404, 400)
    req_id = getattr(g, "request_id", None) or request.environ.get(
        "request_id"
    )
    extra = {"request_id": req_id}
    app.logger.error(
        "HTTP exception: %s %s",
        e.code,
        e.description,
        extra=extra,
    )
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps(
        {"error": e.description, "code": e.code, "request_id": req_id}
    )
    response.content_type = "application/json"
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    # Generic exception handler - logs full traceback and returns JSON
    tb = traceback.format_exc()
    req_id = getattr(g, "request_id", None) or request.environ.get(
        "request_id"
    )
    extra = {"request_id": req_id}
    app.logger.exception(
        "Unhandled exception: %s",
        str(e),
        extra=extra,
    )
    payload = {"error": "Internal Server Error", "request_id": req_id}
    # In debug mode include exception details
    if app.config.get("DEBUG"):
        payload["exception"] = str(e)
        payload["traceback"] = tb
    return jsonify(payload), 500


@app.after_request
def ensure_json_errors(response):
    """Convert default HTML error pages into JSON for consistency.

    Some servers/frameworks return HTML error pages; for API clients
    it's clearer to always return JSON payloads on errors.
    """
    try:
        html_ct = "text/html; charset=utf-8"
        if response.status_code >= 400 and response.content_type == html_ct:
            req_id = getattr(
                request, "request_id", None
            ) or request.environ.get("request_id")
            extra_log = {"request_id": req_id}
            app.logger.info(
                "Converting HTML error response to JSON (status=%s)",
                response.status_code,
                extra=extra_log,
            )
            # Create generic payload
            payload = {
                "error": response.status,
                "code": response.status_code,
                "request_id": req_id,
            }
            # Keep message short
            payload["message"] = response.get_data(as_text=True)[:500]
            resp = jsonify(payload)
            resp.status_code = response.status_code
            return resp
    except Exception:
        app.logger.exception("Failed to convert response to JSON")
    # Ensure the X-Request-ID header is always set for client correlation
    try:
        req_id = getattr(g, "request_id", None) or request.environ.get(
            "request_id"
        )
        if req_id:
            response.headers["X-Request-ID"] = req_id
    except Exception:
        pass
    # Ensure browser clients can read the X-Request-ID header
    try:
        # Ensure Access-Control-Expose-Headers contains unique values
        existing = response.headers.get("Access-Control-Expose-Headers", "")
        expose = "X-Request-ID"
        # Build a set of existing tokens (trim whitespace)
        if existing:
            tokens = {t.strip() for t in existing.split(",") if t.strip()}
        else:
            tokens = set()
        tokens.add(expose)
        if tokens:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(
                sorted(tokens)
            )
    except Exception:
        pass
    return response


@app.errorhandler(404)
def not_found_json(e):
    # Prefer request-scoped id stored in flask.g, fall back to WSGI environ
    req_id = (
        getattr(g, "request_id", None)
        or request.environ.get("request_id")
    )
    app.logger.warning(
        "404 Not Found: %s %s",
        request.method,
        request.path,
        extra={"request_id": req_id},
    )
    return (
        jsonify(
            {
                "error": "Not Found",
                "code": 404,
                "path": request.path,
                "request_id": req_id,
            }
        ),
        404,
    )


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in app.config["ALLOWED_EXTENSIONS"]
    )


# Simple local Whisper transcription endpoint
def _get_local_whisper():
    """Lazily load and cache the local Whisper processor and model.

    Returns tuple (processor, model, model_dir)
    """
    cache = app.config.setdefault("_local_whisper_cache", {})
    if cache.get("processor") and cache.get("model"):
        return cache["processor"], cache["model"], cache.get("model_dir")

    # Prefer locally-downloaded repo under server/models/whisper
    base = os.path.dirname(__file__)
    local_repo = os.path.join(
        base, "server", "models", "whisper", "openai_whisper-large-v3"
    )
    use_repo = (
        local_repo if os.path.isdir(local_repo) else "openai/whisper-large-v3"
    )
    try:
        extra_log = {"request_id": getattr(g, "request_id", "local")}
        app.logger.info(
            "Loading Whisper processor/model from %s",
            use_repo,
            extra=extra_log,
        )
    except Exception:
        app.logger.info("Loading Whisper processor/model (no request context)")

    try:
        # Ensure CUDA is available - enforce GPU only for inference
        import torch as _torch

        if not _torch.cuda.is_available():
            raise RuntimeError(
                "CUDA GPU not available; endpoint requires a GPU."
            )

        # Import heavy transformers classes lazily to avoid blocking startup
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

        processor = AutoProcessor.from_pretrained(use_repo)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(use_repo)
        # Move model to GPU
        model.to(_torch.device("cuda"))
        cache["processor"] = processor
        cache["model"] = model
        cache["model_dir"] = use_repo
        return processor, model, use_repo
    except Exception as e:
        # Surface a clear message for clients when GPU is missing
        try:
            extra_log = {"request_id": getattr(g, "request_id", "local")}
            app.logger.exception(
                "Failed to load local Whisper model: %s", str(e)
            )
        except Exception:
            pass
        raise


@app.route("/ai/transcribe", methods=["POST"])
def ai_transcribe():
    """Transcribe uploaded audio using local Whisper model.

    Accepts multipart/form-data with key 'file' (audio file) or
    JSON body {"audio_path": "path/to/file"}.

    Returns JSON: {"text": ..., "duration": seconds}
    """

    req_id = getattr(g, "request_id", None) or str(uuid.uuid4())
    try:
        # Determine audio source: multipart upload or JSON audio_path
        if (
            request.content_type
            and request.content_type.startswith("multipart/")
            and "file" in request.files
        ):
            f = request.files["file"]
            if f.filename == "":
                return (
                    jsonify(
                        {"error": "No file provided", "request_id": req_id}
                    ),
                    400,
                )
            if not allowed_file(f.filename):
                return (
                    jsonify(
                        {
                            "error": "File extension not allowed",
                            "request_id": req_id,
                        }
                    ),
                    400,
                )
            # Guard filename before calling secure_filename
            if not f.filename:
                return (
                    jsonify(
                        {
                            "error": "No filename provided",
                            "request_id": req_id,
                        }
                    ),
                    400,
                )
            filename = secure_filename(str(f.filename))
            out_dir = os.path.join(app.root_path, "uploads", "temp")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"{uuid.uuid4()}_{filename}")
            f.save(path)
        else:
            data = request.get_json(silent=True) or {}
            path = data.get("audio_path")
            if not path or not os.path.isfile(path):
                return (
                    jsonify(
                        {
                            "error": (
                                "audio_path missing or file does not exist"
                            ),
                            "request_id": req_id,
                        }
                    ),
                    400,
                )

        # Load audio to validate and compute duration later
        try:
            audio, sr = sf.read(path)
        except Exception as e:
            try:
                app.logger.exception("Failed to read audio: %s", str(e))
            except Exception:
                pass
            return (
                jsonify(
                    {
                        "error": "Failed to read audio file",
                        "request_id": req_id,
                    }
                ),
                500,
            )

        # Use the Whisper processor/manager to perform GPU-only transcription.
        # The processors layer enforces the "NIKADA CPU" policy and will raise
        # a RuntimeError if a CUDA GPU is not available.
        try:
            file_id = str(uuid.uuid4())
            body = request.get_json(silent=True) or {}
            model_variant = (
                body.get("model_variant") or request.args.get("model_variant")
            )
            processor = get_processor("whisper")
            res = processor.process(
                file_id=file_id, input_file=path, model_variant=model_variant
            )
        except RuntimeError as re:
            try:
                app.logger.warning(
                    "Whisper request rejected (GPU required): %s", str(re)
                )
            except Exception:
                pass
            return jsonify({"error": str(re), "request_id": req_id}), 503
        except Exception as e:
            app.logger.exception(
                "Transcription failed via WhisperManager: %s", str(e)
            )
            return (
                jsonify(
                    {"error": "Transcription failed", "request_id": req_id}
                ),
                500,
            )

        # Compute duration as a best-effort (soundfile preferred)
        try:
            with sf.SoundFile(str(path)) as sfh:
                duration = float(len(sfh)) / float(sfh.samplerate)
        except Exception:
            duration = float(len(audio) / sr) if "audio" in locals() else 0.0

        # Persist a small metadata summary in outputs/ai_transcriptions
        out_meta_dir = os.path.join(
            app.root_path, "outputs", "ai_transcriptions"
        )
        os.makedirs(out_meta_dir, exist_ok=True)
        meta_path = os.path.join(out_meta_dir, f"transcription_{file_id}.json")
        meta = {
            "text": res.get("text", ""),
            "duration": duration,
            "model": res.get("model"),
            "files": res.get("files", {}),
            "output_dir": res.get("output_dir"),
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as mh:
                json.dump(meta, mh, ensure_ascii=False, indent=2)
        except Exception:
            try:
                app.logger.exception("Failed to write transcription meta")
            except Exception:
                pass

        return jsonify({
            "text": meta["text"],
            "duration": meta["duration"],
            "meta_path": meta_path,
            "files": meta.get("files"),
            "output_dir": meta.get("output_dir"),
            "request_id": req_id,
        })
    except Exception as e:
        app.logger.exception("Unexpected error in ai_transcribe: %s", str(e))
        return (
            jsonify({
                "error": "Internal server error",
                "request_id": getattr(g, "request_id", None),
            }),
            500,
        )


def get_file_extension(filename):
    """Get file extension from filename."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    import time

    response = jsonify(
        {
            "status": "healthy",
            "message": "AI Model Backend with WebSocket support is running",
            "available_models": list(app.config["MODELS"].keys()),
            "websocket_support": True,
            "transcription_endpoint": "/transcribe",
            "timestamp": int(time.time()),
            "server_type": "ai-backend",
        }
    )
    # Add cache control to prevent duplicate rapid requests
    response.headers["Cache-Control"] = "public, max-age=5"
    return response


@app.route("/health/health", methods=["GET"])
def health_check_duplicate():
    """Health check endpoint - handles duplicate path issue from frontend."""
    return health_check()


@app.route("/health/status", methods=["GET"])
def health_status_check():
    """Health status endpoint - alternative health check path."""
    return health_check()


@app.route("/status", methods=["GET"])
def status():
    """Simple status endpoint for frontend connection testing."""
    return jsonify({"status": "ok"})


@app.route("/songs", methods=["GET"])
def list_uploaded_songs():
    """Return a list of uploaded song files with metadata."""
    try:
        # Get base URL from request for absolute URLs
        base_url = request.url_root.rstrip("/")

        upload_folder = app.config["UPLOAD_FOLDER"]
        files = []
        excluded = {".gitkeep", ".gitignore", "README.md"}
        for entry in os.listdir(upload_folder):
            # Skip hidden files and known non-audio entries
            if entry.startswith(".") or entry in excluded:
                continue

            file_path = os.path.join(upload_folder, entry)
            if os.path.isfile(file_path):
                # Extract file_id from filename (uuid.extension)
                file_id = entry.rsplit(".", 1)[0] if "." in entry else entry

                # Skip if file_id is empty (shouldn't happen, but defensive)
                if not file_id or file_id.strip() == "":
                    continue

                # Try to get original filename from outputs metadata
                output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)
                original_filename = entry
                title = None
                artist = None

                # Check if metadata file exists
                metadata_file = os.path.join(output_dir, "metadata.json")
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            original_filename = metadata.get(
                                "original_filename", entry
                            )
                            title = metadata.get("title")
                            artist = metadata.get("artist")
                    except Exception:
                        pass

                # Parse from original_filename if title/artist not in metadata
                if not title or not artist:
                    if "." in original_filename:
                        clean_name = original_filename.rsplit(".", 1)[0]
                    else:
                        clean_name = original_filename

                    if " - " in clean_name:
                        parts = clean_name.split(" - ", 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()
                    else:
                        title = clean_name
                        artist = "Unknown Artist"

                # Get audio duration if available
                duration = None
                try:
                    import mutagen

                    audio = mutagen.File(file_path)
                    if audio and hasattr(audio.info, "length"):
                        duration = int(audio.info.length)
                except Exception:
                    pass

                files.append(
                    {
                        "file_id": file_id,
                        "filename": original_filename,
                        "title": title,
                        "artist": artist,
                        "duration": duration,
                        "size_bytes": os.path.getsize(file_path),
                        "url": "{}/download/{}".format(base_url, file_id),
                    }
                )
        return jsonify({"songs": files, "count": len(files)})
    except Exception as e:
        app.logger.error(f"Failed to list songs: {str(e)}")
        return jsonify({"error": f"Failed to list songs: {str(e)}"}), 500


@app.route("/songs/<file_id>", methods=["DELETE", "OPTIONS"])
def delete_song(file_id):
    """Delete a song file from uploads and outputs folders."""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        deleted_files = []

        # Delete from uploads folder
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        upload_files = list(upload_folder.glob(f"{file_id}.*"))
        for file_path in upload_files:
            file_path.unlink()
            deleted_files.append(str(file_path))

        # Delete from outputs folder
        output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id
        if output_folder.exists():
            import shutil

            shutil.rmtree(output_folder)
            deleted_files.append(str(output_folder))

        # Also check Demucs model directories
        model_dirs = ["htdemucs", "htdemucs_ft", "htdemucs_6s"]
        output_base = Path(app.config["OUTPUT_FOLDER"])
        for model_dir in model_dirs:
            model_output = output_base.joinpath(model_dir, file_id)
            if model_output.exists():
                import shutil

                shutil.rmtree(model_output)
                deleted_files.append(str(model_output))

        if deleted_files:
            response = jsonify(
                {
                    "message": "Song deleted successfully",
                    "deleted_files": deleted_files,
                }
            )
        else:
            response = (
                jsonify(
                    {
                        "message": "No files found for this song",
                        "file_id": file_id,
                    }
                ),
                404,
            )

        # Add CORS headers
        if isinstance(response, tuple):
            response[0].headers["Access-Control-Allow-Origin"] = "*"
            return response
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

    except Exception as e:
        app.logger.error(f"Failed to delete song {file_id}: {str(e)}")
        response = jsonify({"error": f"Failed to delete song: {str(e)}"}), 500
        response[0].headers["Access-Control-Allow-Origin"] = "*"
        return response


@app.route("/models", methods=["GET"])
def list_models():
    """List all available models and their configurations."""
    # Convert sets to lists for JSON serialization
    models_json = {}
    for model_name, config in app.config["MODELS"].items():
        models_json[model_name] = {
            **config,
            "file_types": list(config["file_types"]),
            "available_models": list(config["available_models"]),
        }

    return jsonify({"models": models_json, "message": "Available AI models"})


@app.route("/models/<model_name>", methods=["GET"])
def get_model_info(model_name):
    """Get information about a specific model."""
    if model_name not in app.config["MODELS"]:
        return jsonify({"error": f"Model {model_name} not found"}), 404

    config = app.config["MODELS"][model_name]
    # Convert sets to lists for JSON serialization
    config_json = {
        **config,
        "file_types": list(config.get("file_types", set())),
        "available_models": list(config.get("available_models", [])),
    }

    return jsonify({"model": model_name, "config": config_json})


@app.route("/songs", methods=["GET"])
def list_songs():
    """List all uploaded and processed songs."""
    songs = []

    # Scan uploads folder
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    if upload_folder.exists():
        for file_path in upload_folder.iterdir():
            if file_path.is_file():
                file_id = file_path.stem
                songs.append(
                    {
                        "file_id": file_id,
                        "filename": file_path.name,
                        "status": "uploaded",
                        "size": file_path.stat().st_size,
                        "upload_date": file_path.stat().st_mtime,
                        "download_url": f"/download/{file_id}",
                    }
                )

    # Scan outputs folder (check both direct and Demucs nested structure)
    output_base = Path(app.config["OUTPUT_FOLDER"])
    if output_base.exists():
        # Check direct outputs (e.g., outputs/file_id/)
        for output_folder in output_base.iterdir():
            if output_folder.is_dir():
                file_id = output_folder.name

                # Skip model directories (htdemucs, whisper, etc.)
                if file_id in ["htdemucs", "htdemucs_ft", "htdemucs_6s"]:
                    continue

                existing = next(
                    (s for s in songs if s["file_id"] == file_id), None
                )

                if existing:
                    existing["status"] = "processed"
                    existing["processed_files"] = [
                        f.name for f in output_folder.rglob("*") if f.is_file()
                    ]
                else:
                    songs.append(
                        {
                            "file_id": file_id,
                            "filename": f"{file_id} (processed)",
                            "status": "processed",
                            "processed_files": [
                                f.name
                                for f in output_folder.rglob("*")
                                if f.is_file()
                            ],
                            "download_url": f"/download/{file_id}",
                        }
                    )

        # Check Demucs model directories (e.g., outputs/htdemucs/file_id/)
        for model_dir in output_base.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith("htdemucs"):
                for track_folder in model_dir.iterdir():
                    if track_folder.is_dir():
                        file_id = track_folder.name

                        existing = next(
                            (s for s in songs if s["file_id"] == file_id), None
                        )

                        if existing:
                            existing["status"] = "processed"
                            existing["processed_files"] = [
                                f.name
                                for f in track_folder.rglob("*")
                                if f.is_file()
                            ]
                        else:
                            songs.append(
                                {
                                    "file_id": file_id,
                                    "filename": f"{file_id} (processed)",
                                    "status": "processed",
                                    "processed_files": [
                                        f.name
                                        for f in track_folder.rglob("*")
                                        if f.is_file()
                                    ],
                                    "download_url": f"/download/{file_id}",
                                }
                            )

    return jsonify({"songs": songs, "count": len(songs)})


def check_duplicate_upload(filename):
    """Check if file with same name already exists in outputs."""
    output_folder = app.config["OUTPUT_FOLDER"]
    if not os.path.exists(output_folder):
        return None

    # Search through all existing output directories
    for dir_name in os.listdir(output_folder):
        dir_path = os.path.join(output_folder, dir_name)
        if not os.path.isdir(dir_path):
            continue

        # Check metadata.json for original filename
        metadata_path = os.path.join(dir_path, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    if metadata.get("original_filename") == filename:
                        return dir_name  # Return file_id
            except Exception:
                pass
    return None


def check_output_exists(file_id, output_type):
    """Check if specific output already exists for file_id.

    Args:
        file_id: UUID of the file
        output_type: 'vocals', 'instrumental', 'transcription', 'karaoke'

    Returns:
        Path to existing file if found, None otherwise
    """
    output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)
    if not os.path.exists(output_dir):
        return None

    # Define what files to check for each output type
    patterns = {
        "vocals": ["vocals.mp3", "vocals.wav"],
        "instrumental": [
            "no_vocals.mp3",
            "no_vocals.wav",
            "instrumental.mp3",
            "instrumental.wav",
        ],
        "transcription": ["transcription_base.txt", "transcription_base.json"],
        "karaoke": ["karaoke.lrc"],
    }

    if output_type not in patterns:
        return None

    for pattern in patterns[output_type]:
        file_path = os.path.join(output_dir, pattern)
        if os.path.exists(file_path):
            return file_path

    return None


@app.route("/upload", methods=["POST"])
@app.route("/upload/<model_name>", methods=["POST"])
def upload_file(model_name="demucs"):
    """Upload file for AI processing."""
    try:
        # Request-scoped id for logging and responses
        req_id = (
            getattr(g, "request_id", None) or request.environ.get("request_id")
        )
        if model_name not in app.config["MODELS"]:
            return jsonify({"error": f"Model {model_name} not found"}), 404

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        original_filename = file.filename or ""
        if not original_filename:
            return jsonify({"error": "No file selected"}), 400

        # Check for duplicate upload
        existing_file_id = check_duplicate_upload(original_filename)
        if existing_file_id:
            print(
                "Duplicate upload detected: %s (existing file_id: %s)"
                % (original_filename, existing_file_id)
            )

            return (
                jsonify(
                    {
                        "error": "Song already exists",
                        "file_id": existing_file_id,
                        "message": "This song has already been uploaded",
                        "existing": True,
                    }
                ),
                409,
            )

        model_config = app.config["MODELS"][model_name]
        file_extension = get_file_extension(original_filename)

        if file_extension not in model_config["file_types"]:
            return jsonify(
                {
                    "error": f"File type not supported for {model_name}",
                    "supported_formats": list(model_config["file_types"]),
                },
                400,
            )

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        if not original_filename:
            return (
                jsonify(
                    {
                        "error": "Original filename missing",
                        "request_id": req_id,
                    }
                ),
                400,
            )
        filename = secure_filename(str(original_filename))
        file_extension = get_file_extension(filename)
        artist = None
        song_name = None
        if "-" in original_filename:
            parts = original_filename.split("-")
            artist = parts[0].strip()
            # Remove extension from song name (if available)
            if len(parts) > 1:
                song_name = parts[1].rsplit(".", 1)[0].strip()
            else:
                song_name = None

        # Extract artist from filename if present (before '-')
        original_filename = file.filename
        if not original_filename:
            return (
                jsonify(
                    {
                        "error": "Original filename missing",
                        "request_id": req_id,
                    }
                ),
                400,
            )
        filename = secure_filename(str(original_filename))
        file_extension = get_file_extension(filename)
        artist = None
        if "-" in original_filename:
            artist = original_filename.split("-")[0].strip()

        # Create progress tracker early for upload tracking
        from progress_tracker import create_progress_tracker

        tracker = create_progress_tracker(socketio, file_id)

        # Emit upload start
        tracker.emit_progress("upload", 0, "Starting upload: %s" % filename)

        # Save uploaded file
        upload_path = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{file_id}.{file_extension}"
        )
        file.save(upload_path)

        # Create output directory and save metadata
        output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)
        os.makedirs(output_dir, exist_ok=True)

        # Build metadata with safe line lengths
        if song_name:
            title_val = song_name
        elif "." in original_filename:
            title_val = original_filename.rsplit(".", 1)[0]
        else:
            title_val = original_filename

        metadata = {
            "file_id": file_id,
            "original_filename": original_filename,
            "filename": filename,
            "title": title_val,
            "artist": artist if artist else "Unknown Artist",
            "upload_time": datetime.datetime.now().isoformat(),
        }

        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Emit upload complete
        tracker.emit_progress("upload", 100, f"Upload complete: {filename}")

        # Check if auto-process is requested
        auto_process = (
            request.form.get("auto_process", "true").lower() == "true"
        )

        if not auto_process:
            # If no auto-processing, just return upload success
            resp = {
                "file_id": file_id,
                "filename": filename,
                "status": "uploaded",
                "message": "File uploaded successfully",
            }
            if artist:
                resp["artist"] = artist
            if song_name:
                resp["song_name"] = song_name
            return jsonify(resp), 200

        # Auto-process path continues here
        try:
            # Set audio duration for predictions
            # Set audio duration for predictions
            tracker.set_audio_duration(upload_path)

            # Complete upload stage
            tracker.complete_upload()

            model_variant = request.form.get("model_variant")
            if not model_variant:
                model_variant = model_config.get("default_model", "htdemucs")

            print(f"Auto-processing {file_id} with {model_name} model")

            # Start separation with predictive progress
            tracker.start_separation_progress()

            processor = get_processor(model_name)
            result = processor.process(
                file_id, Path(upload_path), model_variant=model_variant
            )

            # Complete separation
            tracker.complete_separation()

            # Auto-transcribe with Whisper or Gemma 3N (for speech-to-text)
            transcription_result = None
            transcription_model = request.form.get(
                "transcription_model", "gemma_3n"
            ).lower()
            transcription_variant = request.form.get(
                "transcription_model_variant", "gemma-2-2b"
            )
            try:
                tracker.start_transcription_progress()
                msg = (
                    f"Auto-transcribing {file_id} with Gemma 3N "
                    f"(variant: {transcription_variant})"
                )
                print(msg)
                gemma_processor = get_processor("gemma_3n")
                transcription_result = gemma_processor.process(
                    file_id,
                    Path(upload_path),
                    model_variant=transcription_variant,
                    task="transcribe",
                )
                print("Gemma 3N transcription completed successfully")
                tracker.complete_transcription()
            except Exception as transcribe_error:
                print(f"Transcription failed: {transcribe_error}")
                tracker.emit_error("transcription", str(transcribe_error))
                pass

            # Auto-analyze with Gemma 3N (for deep audio analysis)
            gemma_analysis = None
            gemma_model = None
            if transcription_result and transcription_model != "gemma_3n":
                try:
                    print("Analyzing audio with Gemma 3N")
                    gemma_processor = get_processor("gemma_3n")
                    gemma_model = request.form.get("gemma_model", "gemma-2-2b")
                    gemma_analysis = gemma_processor.process(
                        file_id,
                        Path(upload_path),
                        model_variant=gemma_model,
                        task="analyze",
                    )
                    print("Gemma 3N analysis completed successfully")
                except Exception as analyze_error:
                    print(f"Gemma 3N analysis failed: {analyze_error}")
                    pass

            # Build enhanced response with download URLs
            tracks_info = []
            if "tracks" in result:
                for track in result["tracks"]:
                    tracks_info.append(
                        {
                            "name": track,
                            "download_url": f"/download/{file_id}/{track}",
                        }
                    )

            # Get output directory info
            output_dir = result.get("output_dir", "")
            available_files = []
            if output_dir and os.path.exists(output_dir):
                # List actual files in output directory
                for f in os.listdir(output_dir):
                    if os.path.isfile(os.path.join(output_dir, f)):
                        file_stat = os.stat(os.path.join(output_dir, f))
                        available_files.append(
                            {
                                "filename": f,
                                "size": file_stat.st_size,
                                "size_mb": round(
                                    file_stat.st_size / (1024 * 1024), 2
                                ),
                            }
                        )

            response_data = {
                "file_id": file_id,
                "filename": filename,
                "original_size": os.path.getsize(upload_path),
                "model": model_name,
                "model_variant": model_variant,
                "status": "completed",
                "tracks": tracks_info
                if tracks_info
                else result.get("tracks", []),
                "files": available_files,
                "download_url": f"/download/{file_id}",
                "message": f"Successfully processed with {model_name}",
                "processing_time": result.get("processing_time", "N/A"),
            }
            if artist:
                response_data["artist"] = artist
            if song_name:
                response_data["song_name"] = song_name

            # Add transcription info if available (from Whisper)
            if transcription_result:
                transcription_text = transcription_result.get("text", "")
                response_data["transcription"] = {
                    "status": "completed",
                    "text": transcription_text,
                    "model": transcription_model,
                    "model_variant": transcription_variant,
                    "output_file": transcription_result.get(
                        "output_text_file", ""
                    ),
                    "download_url": (
                        f"/download/{file_id}/"
                        f'{transcription_result.get("output_text_file", "")}'
                    ),
                }

            # Add Gemma 3N audio analysis if available.
            # This is separate from the main transcription payload.
            if gemma_analysis:
                analysis_summary = gemma_analysis.get("analysis_summary", "")
                response_data["audio_analysis"] = {
                    "status": "completed",
                    "analysis": analysis_summary,
                    "model": "gemma-3n",
                    "model_variant": gemma_model,
                    "output_file": gemma_analysis.get("output_text_file", ""),
                    "download_url": (
                        f"/download/{file_id}/"
                        f'{gemma_analysis.get("output_text_file", "")}'
                    ),
                }

            # Auto-generate karaoke when both separation and
            # transcription have succeeded
            karaoke_result = None
            if transcription_result and result.get("tracks"):
                try:
                    # Start karaoke with predictive progress
                    tracker.start_karaoke_progress()

                    print(f"Auto-generating karaoke for {file_id}")
                    karaoke_processor = get_processor("karaoke")

                    # Find instrumental and vocals paths from Demucs output
                    output_dir_path = result.get("output_dir", "")
                    instrumental_file = None
                    vocals_file = None

                    if output_dir_path and os.path.exists(output_dir_path):
                        for f in os.listdir(output_dir_path):
                            if "no_vocals" in f or "instrumental" in f:
                                instrumental_file = os.path.join(
                                    output_dir_path, f
                                )
                            elif "vocals" in f:
                                vocals_file = os.path.join(output_dir_path, f)

                    if instrumental_file and transcription_result:
                        # Extract actual transcription text from Whisper result
                        # Whisper returns 'transcription' field, not 'text'
                        transcription_text = transcription_result.get(
                            "transcription", ""
                        )

                        # If no transcription field is present,
                        # try reading from the transcription file
                        if not transcription_text:
                            # Try to find any transcription text file
                            text_files = transcription_result.get(
                                "files", {}
                            ).get("text", "")
                            if text_files:
                                transcription_file_path = os.path.join(
                                    output_dir_path, text_files
                                )
                                if os.path.exists(transcription_file_path):
                                    with open(
                                        transcription_file_path,
                                        "r",
                                        encoding="utf-8",
                                    ) as f:
                                        transcription_text = f.read()

                        karaoke_result = karaoke_processor.process(
                            file_id,
                            instrumental_file,
                            vocals_file or upload_path,
                            transcription_text,
                            original_audio_path=upload_path,
                            artist=artist,
                            song_name=song_name,
                        )

                        # Complete karaoke
                        tracker.complete_karaoke()

                        print(
                            f"Karaoke generation completed: {karaoke_result}"
                        )

                        # Add karaoke info to response
                        karaoke_audio = karaoke_result.get(
                            "audio_with_metadata", ""
                        )
                        karaoke_basename = os.path.basename(karaoke_audio)
                        response_data["karaoke"] = {
                            "status": "completed",
                            "karaoke_dir": karaoke_result.get(
                                "karaoke_dir"
                            ),
                            "lrc_file": karaoke_result.get("lrc_file"),
                            "audio_file": karaoke_audio,
                            "total_lines": karaoke_result.get(
                                "total_lines", 0
                            ),
                            "duration": karaoke_result.get("duration", 0),
                            "download_url": (
                                "/download/" + f"{file_id}/" + karaoke_basename
                            ),
                        }
                except Exception as karaoke_error:
                    print(f"Karaoke generation failed: {karaoke_error}")
                    import traceback

                    traceback.print_exc()

                    # Emit error
                    tracker.emit_error("karaoke", str(karaoke_error))

                    # Don't fail the whole upload if karaoke fails
                    response_data["karaoke"] = {
                        "status": "failed",
                        "error": str(karaoke_error),
                    }

            # Emit final completion
            tracker.complete_all()

            return jsonify(response_data), 200

        except Exception as proc_error:
            # If processing fails, still return upload success
            # but include error details in the response
            print(f"Auto-processing failed: {proc_error}")
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "status": "uploaded",
                        "processing_error": str(proc_error),
                        "message": "File uploaded but processing failed",
                    }
                ),
                500,
            )
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route("/process/<model_name>/<file_id>", methods=["POST"])
def process_with_model(model_name, file_id):
    """Process file with specified AI model."""
    try:
        # Enforce GPU-only for AI processing to respect project policy
        try:
            from models import require_gpu_or_raise

            # For models that can run on CPU as acceptable, processors
            # can decide locally. But for heavy models we enforce here
            # to fail fast when no GPU is available.
            require_gpu_or_raise()
        except RuntimeError as gpu_err:
            return jsonify({"error": str(gpu_err)}), 503
        except Exception:
            # If helper not available, continue and let processors
            # perform checks
            pass
        if model_name not in app.config["MODELS"]:
            return jsonify({"error": f"Model {model_name} not found"}), 404

        # Find uploaded file
        upload_files = list(
            Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
        )
        if not upload_files:
            return jsonify({"error": "File not found"}), 404

        input_file = upload_files[0]

        # Get processing parameters from request
        # (handle both JSON and form data)
        model_variant = None
        try:
            if request.is_json and request.json:
                model_variant = request.json.get("model_variant")
            elif request.form:
                model_variant = request.form.get("model_variant")
        except Exception:
            # If JSON parsing fails, use default model
            pass

        # Use default model if none specified
        if not model_variant:
            model_variant = app.config["MODELS"][model_name]["default_model"]

        # Process with the specified model
        print(f"Processing {file_id} with {model_name} model")
        import time

        start_time = time.time()

        processor = get_processor(model_name)

        # Special handling for karaoke: requires vocals and transcription
        if model_name == "karaoke":
            output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)

            # Find vocals file
            vocals_path = check_output_exists(file_id, "vocals")
            if not vocals_path:
                return (
                    jsonify(
                        {
                            "error": (
                                "Vocals not found. Please run Demucs "
                                "separation first."
                            ),
                            "file_id": file_id,
                            "model": model_name,
                            "status": "failed",
                        }
                    ),
                    400,
                )

            # Find transcription file
            transcription_path = check_output_exists(file_id, "transcription")
            if not transcription_path:
                return (
                    jsonify(
                        {
                            "error": (
                                "Transcription not found. Please run Whisper "
                                "transcription first."
                            ),
                            "file_id": file_id,
                            "model": model_name,
                            "status": "failed",
                        }
                    ),
                    400,
                )

            # Read transcription text
            transcription_text = ""
            if transcription_path.endswith(".txt"):
                with open(transcription_path, "r", encoding="utf-8") as f:
                    transcription_text = f.read()
            elif transcription_path.endswith(".json"):
                with open(transcription_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    transcription_text = data.get("text", "")

            # Get metadata for artist/song name
            metadata_path = os.path.join(output_dir, "metadata.json")
            artist = "Unknown Artist"
            song_name = "Unknown Song"
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    artist = metadata.get("artist", artist)
                    song_name = metadata.get("title", song_name)

            # Call karaoke processor with all required parameters
            result = processor.process(
                file_id,
                input_file,  # instrumental path
                vocals_path,
                transcription_text,
                original_audio_path=input_file,
                artist=artist,
                song_name=song_name,
            )
        else:
            # Check if output already exists (skip redundant processing)
            output_map = {
                "demucs": "vocals",  # Check for vocals.mp3
                "whisper": "transcription",  # Check for transcription_base.txt
            }

            if model_name in output_map:
                existing_output = check_output_exists(
                    file_id, output_map[model_name]
                )
                if existing_output:
                    print(
                        (
                            f"Output already exists for {model_name}: "
                            f"{existing_output}"
                        )
                    )
                    # Return existing result instead of re-processing
                    output_dir = os.path.join(
                        app.config["OUTPUT_FOLDER"], file_id
                    )
                    available_files = []
                    if os.path.exists(output_dir):
                        for f in os.listdir(output_dir):
                            file_path = os.path.join(output_dir, f)
                            if os.path.isfile(file_path):
                                file_stat = os.stat(file_path)
                                available_files.append(
                                    {
                                        "filename": f,
                                        "size": file_stat.st_size,
                                        "size_mb": round(
                                            file_stat.st_size / (1024 * 1024),
                                            2,
                                        ),
                                        "download_url": (
                                            "/download/"
                                            + f"{model_name}/"
                                            + f"{file_id}/"
                                            + f"{f}"
                                        ),
                                    }
                                )

                    return (
                        jsonify(
                            {
                                "file_id": file_id,
                                "model": model_name,
                                "model_variant": model_variant,
                                "status": "completed",
                                "message": (
                                    f"{model_name.title()} output "
                                    f"already exists"
                                ),
                                "files": available_files,
                                "skipped": True,
                                "existing_output": os.path.basename(
                                    existing_output
                                ),
                            }
                        ),
                        200,
                    )

            # Normal processing
            result = processor.process(
                file_id,
                input_file,
                model_variant=model_variant,
            )

        processing_time = round(time.time() - start_time, 2)

        # Build enhanced response with download URLs
        tracks_info = []
        if "tracks" in result:
            for track in result["tracks"]:
                tracks_info.append(
                    {
                        "name": track,
                        "download_url": f"/download/{file_id}/{track}",
                    }
                )

        # Get output directory info
        output_dir = result.get("output_dir", "")
        available_files = []
        if output_dir and os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                file_path = os.path.join(output_dir, f)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    available_files.append(
                        {
                            "filename": f,
                            "size": file_stat.st_size,
                            "size_mb": round(
                                file_stat.st_size / (1024 * 1024), 2
                            ),
                            "download_url": (
                                f"/download/{model_name}/{file_id}/" f"{f}"
                            ),
                        }
                    )

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "model": model_name,
                    "model_variant": model_variant,
                    "status": "completed",
                    "tracks": tracks_info
                    if tracks_info
                    else result.get("tracks", []),
                    "files": available_files,
                    "output_directory": output_dir,
                    "download_url": f"/download/{file_id}",
                    "processing_time_seconds": processing_time,
                    "message": (
                        f"Successfully processed with {model_name} in "
                        f"{processing_time}s"
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Processing error for {model_name}: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": f"{model_name} processing failed: {str(e)}"}),
            500,
        )


@app.route("/separate/<file_id>", methods=["POST"])
def separate_audio(file_id):
    """Start audio separation process (backward compatibility)."""
    try:
        # Find uploaded file
        upload_files = list(
            Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
        )
        if not upload_files:
            return jsonify({"error": "File not found"}), 404

        input_file = upload_files[0]

        # Demucs separation: enforce GPU-only in this deployment
        try:
            from models import require_gpu_or_raise

            require_gpu_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        import sys

        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            app.config["DEMUCS_MODEL"],
            "--mp3",
            "-d",
            "cuda",
            "-o",
            app.config["OUTPUT_FOLDER"],
            str(input_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return (
                jsonify(
                    {"error": "Separation failed", "details": result.stderr}
                ),
                500,
            )

        # Check if separation was successful
        # Demucs creates a subfolder named after the input file
        filename_without_ext = os.path.splitext(os.path.basename(input_file))[
            0
        ]
        expected_output_dir = os.path.join(
            app.config["OUTPUT_FOLDER"],
            app.config["DEMUCS_MODEL"],
            filename_without_ext,
        )
        if not os.path.exists(expected_output_dir):
            return jsonify({"error": "Separation output not found"}), 500

        # List available tracks
        tracks = []
        for track_file in os.listdir(expected_output_dir):
            if track_file.endswith(".mp3"):
                track_name = os.path.splitext(track_file)[0]
                tracks.append(track_name)

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "status": "completed",
                    "tracks": tracks,
                    "message": "Audio separation completed successfully",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Separation failed: {str(e)}"}), 500


@app.route("/download/<file_id>", methods=["GET", "OPTIONS"])
def download_original_file(file_id):
    """Download the original uploaded file or first available output."""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        # First check uploads folder for original file
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        input_files = list(upload_folder.glob(f"{file_id}.*"))

        if input_files:
            file_path = input_files[0]
            # Set correct Content-Type for audio
            mimetype = None
            ext = file_path.suffix.lower()
            if ext == ".mp3":
                mimetype = "audio/mpeg"
            elif ext == ".wav":
                mimetype = "audio/wav"
            elif ext == ".flac":
                mimetype = "audio/flac"
            response = send_file(
                file_path,
                as_attachment=False,  # Stream, not download
                download_name=file_path.name,
                mimetype=mimetype,
            )
            # Add CORS headers for Web Audio API
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        # If not in uploads, check outputs folder
        output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id

        # Also check Demucs model directories
        model_dirs = ["htdemucs", "htdemucs_ft", "htdemucs_6s"]
        demucs_folder = None

        for model_dir in model_dirs:
            potential_path = (
                Path(app.config["OUTPUT_FOLDER"]) / model_dir / file_id
            )
            if potential_path.exists():
                demucs_folder = potential_path
                break

        # Prefer Demucs output if it exists
        search_folder = demucs_folder if demucs_folder else output_folder

        if not search_folder.exists():
            return jsonify({"error": "File not found"}), 404

        # Priority: vocals, instrumental, any wav/mp3
        priority_patterns = [
            "vocals.*",
            "instrumental.*",
            "*.wav",
            "*.mp3",
            "*.flac",
        ]

        for pattern in priority_patterns:
            files = list(search_folder.rglob(pattern))
            if files:
                file_path = files[0]
                # Set correct Content-Type for audio
                mimetype = None
                ext = file_path.suffix.lower()
                if ext == ".mp3":
                    mimetype = "audio/mpeg"
                elif ext == ".wav":
                    mimetype = "audio/wav"
                elif ext == ".flac":
                    mimetype = "audio/flac"
                response = send_file(
                    file_path,
                    as_attachment=False,  # Stream, not download
                    download_name=file_path.name,
                    mimetype=mimetype,
                )
                # Add CORS headers for Web Audio API
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers[
                    "Access-Control-Allow-Methods"
                ] = "GET, OPTIONS"
                response.headers[
                    "Access-Control-Allow-Headers"
                ] = "Content-Type"
                return response

        # If no priority files, return first file found
        all_files = [f for f in search_folder.rglob("*") if f.is_file()]
        if all_files:
            file_path = all_files[0]
            # Set correct Content-Type for audio
            mimetype = None
            ext = file_path.suffix.lower()
            if ext == ".mp3":
                mimetype = "audio/mpeg"
            elif ext == ".wav":
                mimetype = "audio/wav"
            elif ext == ".flac":
                mimetype = "audio/flac"
            response = send_file(
                file_path,
                as_attachment=False,
                download_name=file_path.name,
                mimetype=mimetype,
            )
            # Add CORS headers for Web Audio API
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        return jsonify({"error": "No files available"}), 404

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/download/<model_name>/<file_id>/<filename>", methods=["GET"])
def download_file(model_name, file_id, filename):
    """Download processed files from any model."""
    try:
        if model_name not in app.config["MODELS"]:
            return jsonify({"error": f"Model {model_name} not found"}), 404

        file_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)

        # For Demucs, the outputs are in a model-specific subdirectory
        if model_name == "demucs":
            file_dir = os.path.join(
                app.config["OUTPUT_FOLDER"],
                app.config["DEMUCS_MODEL"],
                file_id,
            )

        file_path = os.path.join(file_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"{file_id}_{filename}",
        )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/download/<file_id>/<track>", methods=["GET"])
def download_track(file_id, track):
    """Download separated audio track or karaoke files."""
    try:
        # First, check karaoke directory (Karaoke-pjesme/file_id/)
        karaoke_dir = os.path.join(
            app.config["OUTPUT_FOLDER"], "Karaoke-pjesme", file_id
        )

        if os.path.exists(karaoke_dir):
            # Look for the requested file in karaoke folder
            for filename in os.listdir(karaoke_dir):
                if track in filename or filename == track:
                    file_path = os.path.join(karaoke_dir, filename)
                    return send_file(
                        file_path, as_attachment=True, download_name=filename
                    )

        # If not in karaoke folder, check Demucs output
        track_dir = os.path.join(
            app.config["OUTPUT_FOLDER"],
            file_id,
            app.config["DEMUCS_MODEL"],
        )

        # Find the track file
        track_files = list(Path(track_dir).glob(f"{track}.*"))
        if not track_files:
            return jsonify({"error": "Track not found"}), 404

        track_file = track_files[0]

        return send_file(
            track_file,
            as_attachment=True,
            download_name=f"{file_id}_{track}.{track_file.suffix[1:]}",
        )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/status/<file_id>", methods=["GET"])
def get_status(file_id):
    """Get separation status for a file."""
    try:
        # Check if upload exists
        upload_files = list(
            Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
        )
        if not upload_files:
            return jsonify({"error": "File not found"}), 404

        # Check if separation is complete
        output_dir = os.path.join(
            app.config["OUTPUT_FOLDER"],
            file_id,
            app.config["DEMUCS_MODEL"],
        )

        if os.path.exists(output_dir):
            tracks = []
            for track_file in os.listdir(output_dir):
                if track_file.endswith((".wav", ".mp3", ".flac")):
                    track_name = os.path.splitext(track_file)[0]
                    tracks.append(track_name)

            return (
                jsonify(
                    {
                        "file_id": file_id,
                        "status": "completed",
                        "tracks": tracks,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {"file_id": file_id, "status": "uploaded", "tracks": []}
                ),
                200,
            )

    except Exception as e:
        return jsonify({"error": f"Status check failed: {str(e)}"}), 500


@app.route("/gpu-status", methods=["GET"])
def gpu_status():
    """Return lightweight GPU / Torch status for frontend checks.

    This endpoint intentionally avoids loading heavy models. It only
    imports torch (if available) and reports CUDA availability and
    device names. Returns 200 with JSON, or 200 with 'available': False
    when torch is missing.
    """
    try:
        try:
            import torch
        except Exception:
            return (
                jsonify(
                    {
                        "available": False,
                        "torch_installed": False,
                        "message": "PyTorch not installed",
                    }
                ),
                200,
            )

        cuda_available = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_available else 0
        devices = []
        if cuda_available and device_count > 0:
            for i in range(device_count):
                try:
                    devices.append(torch.cuda.get_device_name(i))
                except Exception:
                    devices.append(f"cuda:{i}")

        return (
            jsonify(
                {
                    "available": cuda_available,
                    "torch_installed": True,
                    "torch_version": torch.__version__,
                    "cuda_available": cuda_available,
                    "gpu_count": device_count,
                    "devices": devices,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"available": False, "error": str(e)}), 200


@app.route("/cleanup/<file_id>", methods=["DELETE"])
def cleanup_files(file_id):
    """Clean up uploaded and output files for a given file_id."""
    try:
        deleted_files = []

        # Remove uploaded file
        upload_files = list(
            Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
        )
        for upload_file in upload_files:
            os.remove(upload_file)
            deleted_files.append(str(upload_file))

        # Remove output directory
        output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            deleted_files.append(output_dir)

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "message": "Files cleaned up successfully",
                    "deleted_files": deleted_files,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500


@app.route("/karaoke/songs", methods=["GET"])
def list_karaoke_songs():
    """List all available karaoke songs with metadata."""
    try:
        # Get API base URL from request or config
        API_BASE_URL = request.url_root.rstrip("/")

        karaoke_base = os.path.join(
            app.config["OUTPUT_FOLDER"], "Karaoke-pjesme"
        )

        if not os.path.exists(karaoke_base):
            return jsonify({"songs": [], "count": 0}), 200

        songs = []

        for file_dir in os.listdir(karaoke_base):
            file_path = os.path.join(karaoke_base, file_dir)
            if not os.path.isdir(file_path):
                continue

            file_id = file_dir

            # Initialize song data with defaults
            title = None
            artist = None
            duration = None
            audio_url = None

            # Look for sync metadata
            sync_file = os.path.join(file_path, f"{file_id}_sync.json")
            metadata_file = os.path.join(file_path, "metadata.json")

            song_data = {
                "id": file_id,
                "file_id": file_id,
                "karaoke_dir": f"/karaoke/{file_id}",
                "files": {},
            }

            # Load metadata.json if exists (from upload)
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        import json

                        meta = json.load(f)
                        title = meta.get("title")
                        artist = meta.get("artist")
                        duration = meta.get("duration")
                except Exception as e:
                    print(f"Error loading metadata.json for {file_id}: {e}")

            # Load sync metadata if exists
            if os.path.exists(sync_file):
                try:
                    with open(sync_file, "r", encoding="utf-8") as f:
                        import json

                        metadata = json.load(f)
                        if not duration:
                            duration = metadata.get("duration")
                        song_data["total_lines"] = metadata.get("total_lines")
                        song_data["generated_at"] = metadata.get(
                            "generated_at"
                        )
                except Exception as e:
                    print(f"Error loading sync metadata for {file_id}: {e}")

            # Parse title/artist from file_id if not in metadata
            if not title or not artist:
                clean_id = file_id
                if " - " in clean_id:
                    parts = clean_id.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                else:
                    title = clean_id
                    artist = "Unknown Artist"

            # List available files
            for filename in os.listdir(file_path):
                filepath = os.path.join(file_path, filename)
                if os.path.isfile(filepath):
                    file_ext = os.path.splitext(filename)[1].lower()

                    if file_ext == ".lrc":
                        song_data["files"][
                            "lrc"
                        ] = f"/karaoke/{file_id}/{filename}"
                    elif file_ext in [".mp3", ".wav", ".ogg"]:
                        audio_url = (
                            f"{API_BASE_URL}/karaoke/{file_id}/{filename}"
                        )
                        song_data["files"][
                            "audio"
                        ] = f"/karaoke/{file_id}/{filename}"
                    elif file_ext == ".json":
                        song_data["files"][
                            "metadata"
                        ] = f"/karaoke/{file_id}/{filename}"

            # Add required fields for frontend Song type
            song_data["title"] = title or "Unknown Title"
            song_data["artist"] = artist or "Unknown Artist"
            song_data["duration"] = duration or 0
            song_data["url"] = audio_url or song_data["files"].get("audio", "")

            # Only add songs that have audio files
            if audio_url or song_data["files"].get("audio"):
                songs.append(song_data)

        # Sort by generated_at (newest first)
        songs.sort(key=lambda x: x.get("generated_at", ""), reverse=True)

        return jsonify({"songs": songs, "count": len(songs)}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to list songs: {str(e)}"}), 500


@app.route("/karaoke/<file_id>/<filename>", methods=["GET"])
def serve_karaoke_file(file_id, filename):
    """Serve karaoke files (audio, LRC, metadata)."""
    try:
        karaoke_dir = os.path.join(
            app.config["OUTPUT_FOLDER"], "Karaoke-pjesme", file_id
        )

        if not os.path.exists(karaoke_dir):
            return jsonify({"error": "Karaoke not found"}), 404

        file_path = os.path.join(karaoke_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Determine mimetype
        file_ext = os.path.splitext(filename)[1].lower()

        mimetype_map = {
            ".mp3": "audio/mpeg",
            ".lrc": "text/plain",
            ".json": "application/json",
        }

        mimetype = mimetype_map.get(file_ext, "application/octet-stream")

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to serve file: {str(e)}"}), 500


@app.route("/sync-lyrics/<file_id>", methods=["POST"])
def sync_lyrics_with_audio(file_id):
    """
    Analyze audio and generate word-level timing for lyrics sync.
    Uses Gemma 3N's word timing analysis for precise synchronization.

    Request body:
        {
            "transcription": "lyrics text to sync",
            "audio_type": "vocals" | "original" (optional, default: vocals)
        }

    Returns:
        {
            "word_timings": [
                {
                    "word": "...",
                    "start_time": 0.0,
                    "end_time": 0.5,
                    "confidence": 0.85,
                },
                ...
            ],
            "lrc_format": "[00:00.00]First line\\n[00:05.00]Second line...",
            "total_words": 150,
            "duration": 180.5
        }
    """
    try:
        data = request.get_json()
        transcription = data.get("transcription", "")
        audio_type = data.get("audio_type", "vocals")

        if not transcription:
            return jsonify({"error": "Transcription text required"}), 400

        # Find audio file (vocals or original)
        output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"error": "Song not found"}), 404

        # Locate audio file
        audio_path = None
        if audio_type == "vocals":
            vocals_candidates = [
                os.path.join(output_dir, "vocals.mp3"),
                os.path.join(output_dir, "vocals.wav"),
            ]
            for candidate in vocals_candidates:
                if os.path.exists(candidate):
                    audio_path = candidate
                    break

        if not audio_path:
            # Fallback to original audio
            metadata_path = os.path.join(output_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    original_filename = metadata.get("original_filename")
                    if original_filename:
                        audio_path = os.path.join(
                            app.config["UPLOAD_FOLDER"], original_filename
                        )

        if not audio_path or not os.path.exists(audio_path):
            return (
                jsonify(
                    {
                        "error": "Audio file not found. "
                        "Please run vocal separation first."
                    }
                ),
                404,
            )

        # Use Gemma 3N processor's word timing analysis
        from models import PROCESSORS

        gemma_processor = PROCESSORS["gemma_3n"](
            {"default_model": "gemma-2-2b-it"}
        )

        print(f"Analyzing audio timing: {audio_path}")
        word_timings = gemma_processor.analyze_word_timing(
            audio_path, transcription
        )

        if not word_timings:
            return jsonify({"error": "Failed to generate word timings"}), 500

        # Convert to LRC format (group words into lines)
        lrc_lines = []
        words_per_line = 8  # Average words per line

        for i in range(0, len(word_timings), words_per_line):
            line_timings = word_timings[i:i + words_per_line]
            if line_timings:
                start_time = line_timings[0]["start_time"]
                line_text = " ".join([wt["word"] for wt in line_timings])

                minutes = int(start_time // 60)
                seconds = start_time % 60
                lrc_timestamp = f"[{minutes:02d}:{seconds:05.2f}]"
                lrc_lines.append(f"{lrc_timestamp}{line_text}")

        lrc_format = "\n".join(lrc_lines)

        # Get audio duration
        import librosa

        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        print(f"✅ Generated {len(word_timings)} word timings for lyrics sync")

        return jsonify(
            {
                "success": True,
                "word_timings": word_timings,
                "lrc_format": lrc_format,
                "total_words": len(word_timings),
                "duration": float(duration),
                "audio_analyzed": os.path.basename(audio_path),
            }
        )

    except Exception as e:
        print(f"Lyrics sync error: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Lyrics sync failed: {str(e)}"}), 500


@app.route("/instrumental/songs", methods=["GET"])
def list_instrumental_songs():
    """List all instrumental (no_vocals) files from Demucs outputs."""
    try:
        API_BASE_URL = request.url_root.rstrip("/")
        output_folder = Path(app.config["OUTPUT_FOLDER"])
        songs = []

        # Check htdemucs directory
        htdemucs_dir = output_folder / "htdemucs"
        if htdemucs_dir.exists():
            for file_dir in htdemucs_dir.iterdir():
                if not file_dir.is_dir():
                    continue

                file_id = file_dir.name

                # Look for no_vocals.mp3 or instrumental file
                instrumental_file = None
                for filename in file_dir.iterdir():
                    if (
                        "no_vocals" in filename.name.lower()
                        or "instrumental" in filename.name.lower()
                    ):
                        instrumental_file = filename
                        break

                if not instrumental_file:
                    continue

                # Get metadata
                title = "Unknown Title"
                duration = None

                # Try to load metadata from outputs/{file_id}/
                metadata_dir = output_folder / file_id
                if metadata_dir.exists():
                    metadata_file = metadata_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(
                                metadata_file, "r", encoding="utf-8"
                            ) as f:
                                import json

                                meta = json.load(f)
                                title = meta.get("title", title)
                                duration = meta.get("duration")
                        except Exception as e:
                            print(f"Error loading metadata for {file_id}: {e}")

                # Get audio duration if not in metadata
                if not duration:
                    try:
                        import librosa

                        y, sr = librosa.load(
                            str(instrumental_file), sr=None, duration=1
                        )
                        duration = librosa.get_duration(
                            path=str(instrumental_file)
                        )
                    except Exception as e:
                        print(f"Error getting duration for {file_id}: {e}")
                        duration = 0

                song_data = {
                    "id": f"instrumental-{file_id}",
                    "file_id": file_id,
                    "title": title,
                    "artist": "Instrumental",
                    "duration": duration or 0,
                    "url": (
                        f"{API_BASE_URL}/instrumental/{file_id}/"
                        f"{instrumental_file.name}"
                    ),
                    "type": "instrumental",
                }

                songs.append(song_data)

        songs.sort(key=lambda x: x.get("title", ""))

        return jsonify({"songs": songs, "count": len(songs)}), 200

    except Exception as e:
        return (
            jsonify({"error": f"Failed to list instrumental songs: {str(e)}"}),
            500,
        )


@app.route("/instrumental/<file_id>/<filename>", methods=["GET"])
def serve_instrumental_file(file_id, filename):
    """Serve instrumental audio files from Demucs outputs."""
    try:
        file_path = (
            Path(app.config["OUTPUT_FOLDER"]) / "htdemucs" / file_id / filename
        )

        if not file_path.exists():
            return jsonify({"error": "Instrumental file not found"}), 404

        return send_file(
            str(file_path),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name=filename,
        )

    except Exception as e:
        return (
            jsonify({"error": f"Failed to serve instrumental file: {str(e)}"}),
            500,
        )


@app.route("/vocal/songs", methods=["GET"])
def list_vocal_songs():
    """List all vocal files from Demucs outputs."""
    try:
        API_BASE_URL = request.url_root.rstrip("/")
        output_folder = Path(app.config["OUTPUT_FOLDER"])
        songs = []

        # Check htdemucs directory
        htdemucs_dir = output_folder / "htdemucs"
        if htdemucs_dir.exists():
            for file_dir in htdemucs_dir.iterdir():
                if not file_dir.is_dir():
                    continue

                file_id = file_dir.name

                # Look for vocals.mp3 file
                vocal_file = None
                for filename in file_dir.iterdir():
                    if (
                        "vocals" in filename.name.lower()
                        and "no_vocals" not in filename.name.lower()
                    ):
                        vocal_file = filename
                        break

                if not vocal_file:
                    continue

                # Get metadata
                artist = "Unknown Artist"
                duration = None

                # Try to load metadata from outputs/{file_id}/
                metadata_dir = output_folder / file_id
                if metadata_dir.exists():
                    metadata_file = metadata_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(
                                metadata_file, "r", encoding="utf-8"
                            ) as f:
                                import json

                                meta = json.load(f)
                                artist = meta.get("artist", artist)
                                duration = meta.get("duration")
                        except Exception as e:
                            print(f"Error loading metadata for {file_id}: {e}")

                # Get audio duration if not in metadata
                if not duration:
                    try:
                        import librosa

                        y, sr = librosa.load(
                            str(vocal_file), sr=None, duration=1
                        )
                        duration = librosa.get_duration(path=str(vocal_file))
                    except Exception as e:
                        print(f"Error getting duration for {file_id}: {e}")
                        duration = 0

                song_data = {
                    "id": f"vocal-{file_id}",
                    "file_id": file_id,
                    "title": "Vocals Only",
                    "artist": artist,
                    "duration": duration or 0,
                    "url": f"{API_BASE_URL}/vocal/{file_id}/{vocal_file.name}",
                    "type": "vocal",
                }

                songs.append(song_data)

        songs.sort(key=lambda x: x.get("artist", ""))

        return jsonify({"songs": songs, "count": len(songs)}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to list vocal songs: {str(e)}"}), 500


@app.route("/vocal/<file_id>/<filename>", methods=["GET"])
def serve_vocal_file(file_id, filename):
    """Serve vocal audio files from Demucs outputs."""
    try:
        file_path = (
            Path(app.config["OUTPUT_FOLDER"]) / "htdemucs" / file_id / filename
        )

        if not file_path.exists():
            return jsonify({"error": "Vocal file not found"}), 404

        return send_file(
            str(file_path),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name=filename,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to serve vocal file: {str(e)}"}), 500


@app.route("/analyze/chroma/<file_id>", methods=["POST"])
def analyze_chroma_features(file_id):
    """Analyze audio file using enhanced chroma features.

    Uses Librosa and Essentia-based combined analysis.
    """
    try:
        # Find the uploaded file
        upload_files = list(
            Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
        )
        if not upload_files:
            return jsonify({"error": "File not found"}), 404

        input_file = upload_files[0]

        # Initialize enhanced chroma analyzer
        analyzer = EnhancedChromaAnalyzer()

        # Perform comprehensive analysis
        analysis_results = analyzer.analyze_audio_file(str(input_file))

        if not analysis_results.get("success", False):
            return (
                jsonify(
                    {
                        "error": "Analysis failed",
                        "details": analysis_results.get(
                            "error", "Unknown error"
                        ),
                    }
                ),
                500,
            )

        # Save detailed analysis results
        analysis_output_dir = os.path.join(
            app.config["OUTPUT_FOLDER"], file_id
        )
        os.makedirs(analysis_output_dir, exist_ok=True)
        analysis_file = os.path.join(
            analysis_output_dir, f"{file_id}_chroma_analysis.json"
        )
        analyzer.save_analysis_results(analysis_results, analysis_file)

        # Return summarized results for the API response
        combined = analysis_results.get("combined_features", {})
        key_info = combined.get("essentia", {})
        tempo_info = combined.get("tempo_analysis", {})
        harmonic = analysis_results.get("harmonic_analysis", {})

        summary = {
            "file_id": file_id,
            "analysis_type": "enhanced_chroma",
            "status": "completed",
            "audio_info": analysis_results.get("audio_info", {}),
            "key_info": {
                "detected_key": key_info.get("key", "Unknown"),
                "key_strength": key_info.get("key_strength", 0.0),
                "scale": key_info.get("scale", "Unknown"),
            },
            "tempo_info": tempo_info,
            "harmonic_complexity": harmonic.get("progression_complexity", 0.0),
            "chord_changes_count": len(harmonic.get("chord_changes", [])),
            "cross_correlation": combined.get("cross_correlation", {}),
            "detailed_analysis_file": f"{file_id}_chroma_analysis.json",
            "message": "Enhanced chroma analysis completed successfully",
        }

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": f"Chroma analysis failed: {str(e)}"}), 500


@app.route("/analyze/batch", methods=["POST"])
def batch_analyze_files():
    """Batch analyze multiple files with enhanced chroma features."""
    try:
        data = request.get_json()
        file_ids = data.get("file_ids", [])

        if not file_ids:
            return jsonify({"error": "No file IDs provided"}), 400

        results = []
        analyzer = EnhancedChromaAnalyzer()

        for file_id in file_ids:
            # Find the uploaded file
            upload_files = list(
                Path(app.config["UPLOAD_FOLDER"]).glob(f"{file_id}.*")
            )
            if not upload_files:
                results.append(
                    {
                        "file_id": file_id,
                        "success": False,
                        "error": "File not found",
                    }
                )
                continue

            input_file = upload_files[0]

            # Perform analysis
            analysis_results = analyzer.analyze_audio_file(str(input_file))

            if analysis_results.get("success", False):
                # Save detailed results
                analysis_output_dir = os.path.join(
                    app.config["OUTPUT_FOLDER"], file_id
                )
                os.makedirs(analysis_output_dir, exist_ok=True)

                analysis_file = os.path.join(
                    analysis_output_dir, f"{file_id}_chroma_analysis.json"
                )
                analyzer.save_analysis_results(analysis_results, analysis_file)

                results.append(
                    {
                        "file_id": file_id,
                        "success": True,
                        "key": analysis_results.get("combined_features", {})
                        .get("essentia", {})
                        .get("key", "Unknown"),
                        "tempo": analysis_results.get("combined_features", {})
                        .get("tempo_analysis", {})
                        .get("librosa_tempo", 0.0),
                        "harmonic_complexity": analysis_results.get(
                            "harmonic_analysis", {}
                        ).get("progression_complexity", 0.0),
                    }
                )
            else:
                results.append(
                    {
                        "file_id": file_id,
                        "success": False,
                        "error": analysis_results.get(
                            "error", "Analysis failed"
                        ),
                    }
                )

        return (
            jsonify(
                {
                    "batch_analysis": True,
                    "total_files": len(file_ids),
                    "successful_analyses": sum(
                        1 for r in results if r.get("success", False)
                    ),
                    "failed_analyses": sum(
                        1 for r in results if not r.get("success", False)
                    ),
                    "results": results,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Batch analysis failed: {str(e)}"}), 500


# MusicGen text-to-music endpoints
@app.route("/generate/text-to-music", methods=["POST"])
def generate_text_to_music():
    """Generate music from text prompt using MusicGen."""
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            return jsonify({"error": "Text prompt is required"}), 400

        # Normalize prompt: accept string or list and coerce to a string safely
        _prompt_raw = data.get("prompt", "")
        if isinstance(_prompt_raw, list):
            # Join list items into a single prompt string
            prompt = " ".join(str(p) for p in _prompt_raw).strip()
        else:
            prompt = str(_prompt_raw).strip()

        if not prompt:
            return jsonify({"error": "Empty text prompt provided"}), 400

        # Generation parameters
        model_variant = data.get("model_variant", "small")
        duration = data.get("duration", 15)  # Default 15 seconds
        temperature = data.get("temperature", 1.0)
        cfg_coeff = data.get("cfg_coeff", 3.0)

        # Validate parameters
        if duration < 1 or duration > 120:
            return (
                jsonify(
                    {"error": "Duration must be between 1 and 120 seconds"}
                ),
                400,
            )

        if temperature < 0.1 or temperature > 2.0:
            return (
                jsonify({"error": "Temperature must be between 0.1 and 2.0"}),
                400,
            )

        if cfg_coeff < 1.0 or cfg_coeff > 10.0:
            return (
                jsonify(
                    {"error": "CFG coefficient must be between 1.0 and 10.0"}
                ),
                400,
            )

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Save prompt to text file for processing
        prompt_file = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{file_id}.txt"
        )
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Process with MusicGen
        processor = get_processor("musicgen")
        result = processor.process(
            file_id,
            prompt_file,
            model_variant=model_variant,
            duration=duration,
            temperature=temperature,
            cfg_coeff=cfg_coeff,
        )

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "model": "musicgen",
                    "prompt": prompt,
                    "status": "completed",
                    "result": result,
                    "message": "Music generation completed successfully",
                    "download_url": (
                        f"/download/{file_id}/generated_{model_variant}.wav"
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Music generation failed: {str(e)}"}), 500


@app.route("/generate/text-to-music/<file_id>", methods=["GET"])
def get_generation_status(file_id):
    """Get status of music generation by file_id."""
    try:
        output_dir = os.path.join(app.config["OUTPUT_FOLDER"], file_id)

        if not os.path.exists(output_dir):
            return jsonify({"error": "Generation not found"}), 404

        # Look for generated files
        generated_files = []
        prompt_files = []

        for file in os.listdir(output_dir):
            if file.startswith("generated_") and file.endswith(".wav"):
                file_path = os.path.join(output_dir, file)
                file_size = os.path.getsize(file_path)
                generated_files.append(
                    {
                        "filename": file,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "download_url": f"/download/{file_id}/{file}",
                    }
                )
            elif file.startswith("prompt_") and file.endswith(".txt"):
                prompt_files.append(file)

        # Read prompt details if available
        prompt_info = {}
        if prompt_files:
            prompt_file = os.path.join(output_dir, prompt_files[0])
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if ":" in line:
                            key, value = line.strip().split(":", 1)
                            prompt_info[key.strip().lower()] = value.strip()
            except Exception:
                pass

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "status": "completed" if generated_files else "processing",
                    "generated_files": generated_files,
                    "prompt_info": prompt_info,
                    "total_files": len(generated_files),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Status check failed: {str(e)}"}), 500


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """HTTP endpoint for audio transcription using Whisper or Gemma 3N."""
    try:
        # Request-scoped id for logging and responses
        req_id = (
            getattr(g, "request_id", None) or request.environ.get("request_id")
        )
        # Check if file is provided
        if "file" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Generate unique file ID
        import uuid

        file_id = str(uuid.uuid4())

        # Save uploaded file
        if not file.filename:
            return (
                jsonify(
                    {"error": "No filename provided", "request_id": req_id}
                ),
                400,
            )
        filename = secure_filename(str(file.filename))
        file_extension = get_file_extension(filename)

        if not allowed_file(filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Save file temporarily
        temp_filename = f"{file_id}.{file_extension}"
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)
        file.save(temp_path)

        # Model selection: whisper (default) or gemma_3n
        model_name = request.form.get("model", "whisper").lower()
        model_variant = request.form.get(
            "model_variant",
            "base" if model_name == "whisper" else "gemma-2-2b",
        )

        if model_name not in ["whisper", "gemma_3n"]:
            return jsonify({"error": f"Invalid model: {model_name}"}), 400

        processor = get_processor(model_name)
        # For Gemma 3N, use task='transcribe'
        if model_name == "gemma_3n":
            result = processor.process(
                file_id,
                temp_path,
                model_variant=model_variant,
                task="transcribe",
            )
            transcription = result.get("analysis_summary", "")
            language = "unknown"  # Gemma 3N may not return language
        else:
            result = processor.process(
                file_id, temp_path, model_variant=model_variant
            )
            transcription = result.get("transcription", "")
            language = result.get("language", "unknown")

        # Clean up temporary file
        try:
            os.remove(temp_path)
        except Exception:
            pass

        return (
            jsonify(
                {
                    "file_id": file_id,
                    "model": model_name,
                    "model_variant": model_variant,
                    "status": "completed",
                    "transcription": transcription,
                    "language": language,
                    "message": (
                        (
                            f"Transcription completed successfully with "
                            f"{model_name}"
                        )
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500


# Global Whisper model for real-time transcription
whisper_model = None


def load_whisper_model(model_size="base"):
    """Load Whisper model for real-time transcription."""
    global whisper_model
    try:
        if whisper_model is None:
            import torch

            # If HF download mode is enabled and a local model dir exists for
            # the configured model, prefer loading from that path.
            try:
                use_hf = app.config.get("WHISPER_USE_HF_DOWNLOAD", False)
                hf_repo = app.config.get("WHISPER_MODEL_REPO")
            except Exception:
                use_hf = False
                hf_repo = None

            if use_hf and hf_repo:
                # Map repo to sanitized folder name used by downloader
                from server.scripts.download_whisper_model import model_dir_for

                local_dir = model_dir_for(hf_repo)
                if local_dir.exists():
                    try:
                        print(
                            f"📦 Loading Whisper from local HF dir: {local_dir}"
                        )
                        whisper_model = whisper.load_model(str(local_dir))
                        print("✅ Whisper model loaded from local dir")
                        return whisper_model
                    except Exception:
                        # Fall back to normal loading below
                        print(
                            (
                                "⚠️ Failed to load Whisper from local dir, "
                                "falling back"
                            )
                        )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            device_info = (
                f" ({torch.cuda.get_device_name(0)})"
                if device == "cuda"
                else " (CPU)"
            )
            print(f"📥 Loading Whisper model: {model_size}")
            print(f"🎮 Using device: {device}{device_info}")
            whisper_model = whisper.load_model(model_size, device=device)
            print(f"✅ Whisper model loaded on {device}")
        return whisper_model
    except Exception as e:
        print(f"❌ Error loading Whisper model: {e}")
        return None


# WebSocket events for real-time transcription
@socketio.on("connect", namespace="/transcribe")
def on_connect():
    """Handle client connection."""
    print("Client connected to transcription namespace")
    emit("connected", {"message": "Connected to transcription service"})


@socketio.on("disconnect", namespace="/transcribe")
def on_disconnect():
    """Handle client disconnection."""
    print("Client disconnected from transcription namespace")


@socketio.on("audio", namespace="/transcribe")
def handle_audio_chunk(data):
    """Handle incoming audio chunks for real-time transcription."""
    try:
        # Load Whisper model if not loaded
        model = load_whisper_model("base")
        if model is None:
            emit("error", {"message": "Failed to load Whisper model"})
            return

        # Decode audio data
        audio_data = data.get("payload", {}).get("data")
        if not audio_data:
            emit("error", {"message": "No audio data provided"})
            return

        # Decode base64 audio data
        try:
            decoded_audio = base64.b64decode(audio_data)
            # Convert to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(decoded_audio, dtype=np.int16)
            audio_array = audio_array.astype(np.float32) / 32768.0

            # Ensure we have enough audio for transcription (minimum 1 second)
            if len(audio_array) < 16000:  # 16kHz sample rate
                return

            # Transcribe audio chunk
            import torch

            use_fp16 = torch.cuda.is_available()
            result = model.transcribe(
                audio_array, language="en", fp16=use_fp16
            )
            transcription = result.get("text", "").strip()

            if transcription:
                emit("transcription", {"transcription": transcription})

        except Exception as decode_error:
            print(f"Audio decoding error: {decode_error}")
            emit(
                "error",
                {"message": f"Audio decoding failed: {str(decode_error)}"},
            )

    except Exception as e:
        print(f"Transcription error: {e}")
        emit("error", {"message": f"Transcription failed: {str(e)}"})


@socketio.on("finish", namespace="/transcribe")
def handle_finish():
    """Handle transcription finish signal."""
    print("Transcription session finished")
    emit("finished", {"message": "Transcription completed"})
    disconnect()


# Serve static files and test UI
@app.route("/test_progress.html")
def serve_test_progress():
    """Serve the test progress UI."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_file(os.path.join(static_dir, "test_progress.html"))


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files."""
    from flask import send_from_directory

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, filename)


# YouTube Download Endpoint
@app.route("/download-youtube", methods=["POST"])
def download_youtube():
    """Download YouTube video/audio and save to uploads folder"""
    try:
        from youtube_downloader import YouTubeDownloader

        data = request.get_json()
        url = data.get("url")
        format_type = data.get("format", "mp3")
        bitrate = data.get("bitrate", "high")

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # Validate format
        valid_formats = ["mp3", "wav", "flac", "mp4"]
        if format_type not in valid_formats:
            return (
                jsonify(
                    {
                        "error": (
                            "Invalid format. Must be one of: "
                            + f"{valid_formats}"
                        )
                    }
                ),
                400,
            )

        # Validate bitrate/quality
        valid_qualities = ["high", "medium", "low"]
        if bitrate not in valid_qualities:
            return (
                jsonify(
                    {
                        "error": (
                            "Invalid quality. Must be one of: "
                            + f"{valid_qualities}"
                        )
                    }
                ),
                400,
            )

        # Initialize downloader with uploads folder
        downloader = YouTubeDownloader(app.config["UPLOAD_FOLDER"])

        # Perform download
        result = downloader.download(url, format_type, bitrate)

        if not result.get("success"):
            # Log the error to backend console for debugging
            print(f"[YouTubeDownloader ERROR] {result.get('error')}")
            # Return full error details to frontend
            return (
                jsonify(
                    {
                        "error": result.get("error", "Unknown error"),
                        "details": result,
                    }
                ),
                500,
            )

        return jsonify(
            {
                "success": True,
                "title": result["title"],
                "filename": result["filename"],
                "format": result["format"],
                "quality": result["quality"],
                "size_mb": result["size_mb"],
                "message": f"Successfully downloaded: {result['title']}",
            }
        )

    except Exception as e:
        print(f"YouTube download error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/youtube-info", methods=["POST"])
def get_youtube_info():
    """Get YouTube video information without downloading"""
    try:
        from youtube_downloader import YouTubeDownloader

        data = request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        downloader = YouTubeDownloader(app.config["UPLOAD_FOLDER"])
        result = downloader.get_video_info(url)

        if not result.get("success"):
            return (
                jsonify(
                    {"error": result.get("error", "Failed to fetch info")}
                ),
                500,
            )

        return jsonify(result)

    except Exception as e:
        print(f"YouTube info error: {e}")
        return jsonify({"error": str(e)}), 500


# Utility: Test all processors with dummy/test data
# Note: self-test imports are intentionally disabled here to avoid
# importing heavy model modules at module import time. If you want to
# run processor self-tests, import `test_all_processors` inside
# the __main__ block where it's used.

if __name__ == "__main__":
    print("Starting AI Multi-Model Backend with WebSocket support...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"Supported formats: {app.config['ALLOWED_EXTENSIONS']}")
    print("WebSocket transcription: /transcribe namespace")

    # Run processor self-test (Gemma3N uses gemma-2-27b-it)
    # TEMPORARILY DISABLED: Demucs self-test crashes the server
    # print("\nRunning processor self-test...")
    # with app.app_context():
    #     test_results = test_all_processors()
    #     print(json.dumps(test_results, indent=2, ensure_ascii=False))
    print("\nWARNING: Model self-tests SKIPPED for faster startup")

    try:
        # Use SocketIO for WebSocket support
        socketio.run(
            app,
            host=app.config["HOST"],
            port=app.config["PORT"],
            debug=app.config["DEBUG"],
            ssl_context=None,  # SSL handled by nginx in production
            allow_unsafe_werkzeug=True,
        )
    except Exception as e:
        print(f"SocketIO failed to start: {e}")
        print("Falling back to regular Flask server...")
        app.run(
            host=app.config["HOST"],
            port=app.config["PORT"],
            debug=app.config["DEBUG"],
            use_reloader=False,
        )
