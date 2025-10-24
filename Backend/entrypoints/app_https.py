#!/usr/bin/env python3
"""
HTTPS-enabled version of the Flask app for production use
"""
import ssl
from app import app, socketio

if __name__ == '__main__':
    print("Starting AI Multi-Model Backend with HTTPS support...")
    print("Upload folder: {}".format(app.config.get('UPLOAD_FOLDER')))
    print("Output folder: {}".format(app.config.get('OUTPUT_FOLDER')))
    print("Supported formats: {}".format(app.config.get('ALLOWED_EXTENSIONS')))
    print("WebSocket transcription available at /transcribe")
    print("HTTPS server will listen on port 443 when certificates are present")

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    # You'll need to generate or obtain SSL certificates
    # For development, you can create self-signed certificates:
    # openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

    try:
        context.load_cert_chain('nginx/ssl/cert.pem', 'nginx/ssl/key.pem')

        # Use SocketIO for WebSocket support with SSL
        socketio.run(
            app,
            host='0.0.0.0',
            port=443,
            debug=False,
            ssl_context=context,
            allow_unsafe_werkzeug=True
        )
    except FileNotFoundError:
        print("SSL certificates not found. Please generate SSL certificates first.")
        print(
            "Run (example): openssl req -x509 -newkey rsa:4096 -nodes -out nginx/ssl/cert.pem"
        )
        print(
            "  -keyout nginx/ssl/key.pem -days 365"
        )
    except Exception as e:
        print(f"HTTPS server failed to start: {e}")
        print("Falling back to HTTP server on port 5000...")
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            allow_unsafe_werkzeug=True
        )
