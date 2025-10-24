"""
Production server for Windows
Uses Flask with production configurations
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import app, socketio

if __name__ == "__main__":
    # Production settings
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"

    print("Starting Multi-Model AI Backend Server with WebSocket support...")
    print("Server: http://{}:{}".format(host, port))
    print("WebSocket: /socket.io/ (for real-time transcription)")
    print("Debug: {}".format(debug))
    print("Upload folder: {}".format(app.config['UPLOAD_FOLDER']))
    print("Output folder: {}".format(app.config['OUTPUT_FOLDER']))
    print("Available models: {}".format(list(app.config['MODELS'].keys())))
    print("Press Ctrl+C to stop")
    print("-" * 50)

    # Use SocketIO for WebSocket support
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,
        ssl_context=None,  # SSL handled by nginx
        allow_unsafe_werkzeug=True,  # Allow Werkzeug in production for simplicity
    )
