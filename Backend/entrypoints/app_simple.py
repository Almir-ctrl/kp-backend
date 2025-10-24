import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-key-change-in-prod'
)

# Configure CORS for production - allow all origins including Google AI Studio
CORS(
    app,
    origins="*",
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    supports_credentials=False,
)

# Initialize config to create directories
config = Config()


def allowed_file(filename):
    """Check if the file extension is allowed."""
    if '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in app.config[
        'ALLOWED_EXTENSIONS'
    ]


def get_file_extension(filename):
    """Get file extension from filename."""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'AI Model Backend is running',
        'available_models': list(app.config['MODELS'].keys()),
        'websocket_support': False,
        'transcription_endpoint': '/transcribe'
    })


@app.route('/health/health', methods=['GET'])
def health_check_duplicate():
    """Health check endpoint - handles duplicate path issue from frontend."""
    return health_check()


@app.route('/health/status', methods=['GET'])
def health_status_check():
    """Health status endpoint - alternative health check path."""
    return health_check()


@app.route('/status', methods=['GET'])
def status():
    """Simple status endpoint for frontend connection testing."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("Starting AI Model Backend (Simple Flask)...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"Supported formats: {app.config['ALLOWED_EXTENSIONS']}")

    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG'],
    )
