import os
import uuid
import base64
import numpy as np
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
import whisper
from config import Config
from models import get_processor
from server.logging_utils import setup_flask_app_hooks

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "your-secret-key-change-in-production"
)

# Configure CORS for production
cors_origins = os.environ.get("CORS_ORIGINS", "*")
if cors_origins != "*":
    cors_origins = cors_origins.split(",")

CORS(app, origins=cors_origins)

# Initialize SocketIO with CORS support
socketio = SocketIO(
    app,
    cors_allowed_origins=cors_origins,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# Initialize config to create directories
config = Config()

# Set up logging, request ID tracking, and error handlers
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
setup_flask_app_hooks(app, log_dir=LOG_DIR, enable_json_converter=True)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Global Whisper model for real-time transcription
whisper_model = None


def load_whisper_model(model_size="base"):
    """Load Whisper model for real-time transcription."""
    global whisper_model
    try:
        if whisper_model is None:
            print(f"Loading Whisper model: {model_size}")
            whisper_model = whisper.load_model(model_size)
            print("Whisper model loaded successfully")
        return whisper_model
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return None


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in app.config["ALLOWED_EXTENSIONS"]
    )


def get_file_extension(filename):
    """Get file extension from filename."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "message": "AI Model Backend is running",
            "available_models": list(app.config["MODELS"].keys()),
            "websocket_support": True,
        }
    )


@app.route("/models", methods=["GET"])
def list_models():
    """List all available models and their configurations."""
    # Convert sets to lists for JSON serialization
    models_json = {}
    for model_name, model_config in app.config["MODELS"].items():
        models_json[model_name] = {
            "file_types": list(model_config["file_types"]),
            "purpose": model_config["purpose"],
        }
    return jsonify(models_json)


@app.route("/songs", methods=["GET"])
def list_songs():
    """List all uploaded and processed songs."""
    songs = []

    # Scan uploads folder
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    if upload_folder.exists():
        for file_path in upload_folder.iterdir():
            if file_path.is_file():
                # Extract file_id from filename (before first dot)
                file_id = file_path.stem
                songs.append({
                    "file_id": file_id,
                    "filename": file_path.name,
                    "status": "uploaded",
                    "size": file_path.stat().st_size,
                    "upload_date": file_path.stat().st_mtime,
                    "download_url": f"/download/{file_id}"
                })

    # Scan outputs folder for processed files
    output_base = Path(app.config["OUTPUT_FOLDER"])
    if output_base.exists():
        for output_folder in output_base.iterdir():
            if output_folder.is_dir():
                file_id = output_folder.name

                # Check if we already have this from uploads
                existing = next(
                    (s for s in songs if s["file_id"] == file_id), None
                )

                if existing:
                    # Update status to processed
                    existing["status"] = "processed"
                    existing["processed_files"] = [
                        f.name for f in output_folder.iterdir()
                        if f.is_file()
                    ]
                else:
                    # Add as processed-only entry
                    songs.append({
                        "file_id": file_id,
                        "filename": f"{file_id} (processed)",
                        "status": "processed",
                        "processed_files": [
                            f.name for f in output_folder.iterdir()
                            if f.is_file()
                        ],
                        "download_url": f"/download/{file_id}"
                    })

    return jsonify({"songs": songs, "count": len(songs)})


@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload a file for processing."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "error": f'File type not allowed. Supported: {app.config["ALLOWED_EXTENSIONS"]}'
                }
            ),
            400,
        )

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())

    # Determine file extension and create appropriate filename
    extension = get_file_extension(filename)
    stored_filename = f"{file_id}.{extension}"

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
    file.save(file_path)

    return jsonify(
        {
            "message": "File uploaded successfully",
            "file_id": file_id,
            "filename": filename,
            "size": os.path.getsize(file_path),
        }
    )


@app.route("/process/<model_name>/<file_id>", methods=["POST"])
def process_file(model_name, file_id):
    """Process a file with the specified model."""
    if model_name not in app.config["MODELS"]:
        return jsonify({"error": f"Model {model_name} not available"}), 400

    # Find the uploaded file
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    input_files = list(upload_folder.glob(f"{file_id}.*"))

    if not input_files:
        return jsonify({"error": "File not found"}), 404

    input_file = input_files[0]

    # Check if file type is supported by the model
    file_extension = input_file.suffix[1:].lower()  # Remove the dot
    if file_extension not in app.config["MODELS"][model_name]["file_types"]:
        supported_types = list(app.config["MODELS"][model_name]["file_types"])
        msg = (
            f"File type .{file_extension} not supported by {model_name}. "
            f"Supported: {supported_types}"
        )
        return jsonify({"error": msg}), 400

    try:
        processor = get_processor(model_name)
        result = processor.process(str(input_file), file_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route("/separate/<file_id>", methods=["POST"])
def separate_audio(file_id):
    """Separate audio using Demucs (legacy endpoint for backward compatibility)."""
    return process_file("demucs", file_id)


@app.route("/status/<file_id>", methods=["GET"])
def get_status(file_id):
    """Get processing status of a file."""
    output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id

    if not output_folder.exists():
        return jsonify({"status": "not_found"}), 404

    # Check for various completion indicators
    status_file = output_folder / "status.txt"
    if status_file.exists():
        with open(status_file, "r") as f:
            status = f.read().strip()
        return jsonify({"status": status})

    # Check if there are any output files (indicates completion for some processors)
    output_files = list(output_folder.rglob("*"))
    if output_files:
        return jsonify({"status": "completed"})

    return jsonify({"status": "processing"})


@app.route("/download/<file_id>", methods=["GET"])
def download_file(file_id):
    """Download the original uploaded file or main processed output."""
    # First check uploads folder for original file
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    input_files = list(upload_folder.glob(f"{file_id}.*"))

    if input_files:
        file_path = input_files[0]
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    # If not in uploads, check outputs folder for processed files
    output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id

    if not output_folder.exists():
        return jsonify({"error": "File not found"}), 404

    # Return the first available output file (prioritize common types)
    priority_patterns = ["*.wav", "*.mp3", "*.flac", "*_vocals.wav", "*_instrumental.wav"]

    for pattern in priority_patterns:
        files = list(output_folder.glob(pattern))
        if files:
            file_path = files[0]
            return send_file(
                file_path,
                as_attachment=True,
                download_name=file_path.name
            )

    # If no priority files found, return any file
    all_files = [f for f in output_folder.iterdir() if f.is_file()]
    if all_files:
        file_path = all_files[0]
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    return jsonify({"error": "No files available for download"}), 404


@app.route("/download/<file_id>/<track_name>", methods=["GET"])
def download_track(file_id, track_name):
    """Download a separated track or processed file."""
    output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id

    if not output_folder.exists():
        return jsonify({"error": "File not found"}), 404

    # Look for the requested track
    possible_extensions = ["wav", "mp3", "flac", "txt", "json"]
    track_file = None

    for ext in possible_extensions:
        potential_file = output_folder / f"{track_name}.{ext}"
        if potential_file.exists():
            track_file = potential_file
            break

    if track_file is None:
        # List available files for debugging
        available_files = [
            f.name for f in output_folder.iterdir() if f.is_file()
        ]
        return (
            jsonify(
                {
                    "error": f'Track "{track_name}" not found',
                    "available_files": available_files,
                }
            ),
            404,
        )

    return send_file(str(track_file), as_attachment=True)


@app.route("/files/<file_id>", methods=["GET"])
def list_files(file_id):
    """List all available files for a processed file_id."""
    output_folder = Path(app.config["OUTPUT_FOLDER"]) / file_id

    if not output_folder.exists():
        return jsonify({"error": "File not found"}), 404

    files = []
    for file_path in output_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(output_folder)
            files.append(
                {
                    "name": str(relative_path),
                    "size": file_path.stat().st_size,
                    "download_url": f"/download/{file_id}/{relative_path.stem}",
                }
            )

    return jsonify({"files": files})


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
            audio_array = (
                np.frombuffer(decoded_audio, dtype=np.int16).astype(np.float32)
                / 32768.0
            )

            # Ensure we have enough audio for transcription (minimum 1 second)
            if len(audio_array) < 16000:  # 16kHz sample rate
                return

            # Transcribe audio chunk
            result = model.transcribe(audio_array, language="en", fp16=False)
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


if __name__ == "__main__":
    # For development
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        ssl_context=None,  # SSL handled by nginx in production
    )
