#!/usr/bin/env python3
"""
Production WSGI server with Gunicorn
Optimized for production deployment
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# When using eventlet we must monkey-patch the stdlib before importing
# modules that use networking/threading. Call monkey_patch early.
try:
    import eventlet

    eventlet.monkey_patch()
except Exception:
    # If eventlet is not installed, continue — other workers (gunicorn gevent) may be used.
    eventlet = None

# Import the Flask-SocketIO socket instance after monkey-patching.
# We avoid importing `app` into the top-level name to prevent redefinition.
from app import socketio as socketio_instance


def create_production_app():
    """Create production-ready app with proper configuration."""
    # Import the Flask app from the application package here so that we do
    # not keep a top-level import that could cause redefinition issues.
    from app import app as flask_app

    # Production settings
    flask_app.config["DEBUG"] = False
    flask_app.config["TESTING"] = False
    flask_app.config["ENV"] = "production"

    # Security settings
    flask_app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION"
    )

    # CORS for production
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    if cors_origins != "*":
        flask_app.config["CORS_ORIGINS"] = cors_origins.split(",")

    return flask_app


if __name__ == "__main__":
    # This should only run in development
    print("WARNING: This is running in development mode!")
    print("For production, use: gunicorn --config gunicorn.conf.py wsgi_production:app")

    app = create_production_app()
    socketio_instance.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=False,
        allow_unsafe_werkzeug=True,
    )
else:
    # Production WSGI application
    app = create_production_app()
