"""Shared logging utilities for Flask apps.

This module provides reusable logging, request ID tracking, and error handling
components that can be shared across multiple Flask applications.
"""

import os
import logging
import uuid
import json
import traceback
from logging.handlers import RotatingFileHandler
from flask import request, jsonify
from werkzeug.exceptions import HTTPException


class RequestIDFilter(logging.Filter):
    """Inject request_id into log records from Flask request context."""

    def filter(self, record):
        try:
            # Try to pull from flask request context or environ
            env_req_id = request.environ.get('request_id', '')
            record.request_id = getattr(request, 'request_id', env_req_id)
        except Exception:
            record.request_id = ''
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record):
        log_obj = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', ''),
        }
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_app_logging(app, log_dir='logs'):
    """Set up logging for a Flask app with request ID support.

    Args:
        app: Flask application instance
        log_dir: Directory to store log files (default: 'logs')
    """
    os.makedirs(log_dir, exist_ok=True)

    # Text log with rotating file handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s'
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIDFilter())
    app.logger.addHandler(file_handler)

    # JSON log with rotating file handler
    json_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.json.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5
    )
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JsonFormatter())
    json_handler.addFilter(RequestIDFilter())
    app.logger.addHandler(json_handler)

    # Also attach to root logger so werkzeug and other modules write to same file
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(json_handler)

    app.logger.setLevel(logging.INFO)

    # Write a startup log entry to validate file logging
    try:
        app.logger.info("Logging initialized", extra={"request_id": "startup"})
    except Exception:
        root_logger.info("Logging initialized")


def add_request_id_hooks(app):
    """Add before_request and after_request hooks for request ID management.

    This function registers Flask hooks that:
    - Generate or accept request IDs for tracing
    - Log incoming requests with context
    - Add X-Request-ID to response headers
    - Ensure CORS exposes X-Request-ID header

    Args:
        app: Flask application instance
    """

    @app.before_request
    def log_request_info():
        """Log basic request info and assign request ID."""
        try:
            # Prefer client-provided X-Request-ID if present
            incoming_req_id = (
                request.headers.get('X-Request-ID')
                or request.headers.get('x-request-id')
            )

            # Generate or accept a request_id for tracing
            request_id = incoming_req_id or str(uuid.uuid4())
            extra = {"request_id": request_id}
            msg = "Request: %s %s from %s"
            app.logger.info(
                msg,
                request.method,
                request.path,
                request.remote_addr,
                extra=extra,
            )

            # Store into Flask environ for later handlers
            request.environ['request_id'] = request_id
        except Exception:
            # In case request context is not fully available
            app.logger.info("Request received")

    @app.after_request
    def add_request_id_header(response):
        """Add X-Request-ID to response headers and ensure CORS exposure."""
        # Set X-Request-ID header
        try:
            req_id = (
                getattr(request, 'request_id', None)
                or request.environ.get('request_id')
            )
            if req_id:
                response.headers['X-Request-ID'] = req_id
        except Exception:
            pass

        # Ensure browser clients can read the X-Request-ID header
        try:
            # Ensure Access-Control-Expose-Headers contains unique values
            existing = response.headers.get('Access-Control-Expose-Headers', '')
            expose = 'X-Request-ID'
            # Build a set of existing tokens (trim whitespace)
            if existing:
                tokens = {t.strip() for t in existing.split(',') if t.strip()}
            else:
                tokens = set()
            tokens.add(expose)
            if tokens:
                response.headers[
                    'Access-Control-Expose-Headers'
                ] = ', '.join(sorted(tokens))
        except Exception:
            pass

        return response


def add_error_handlers(app):
    """Add standard error handlers to Flask app.

    This function registers error handlers that:
    - Convert all errors to JSON format
    - Include request IDs in error responses
    - Log errors with appropriate severity
    - Include debug details when DEBUG=True

    Args:
        app: Flask application instance
    """

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Return JSON for HTTPExceptions (e.g., 404, 400)."""
        req_id = (
            getattr(request, 'request_id', None)
            or request.environ.get('request_id')
        )
        extra = {"request_id": req_id}
        app.logger.error(
            "HTTP exception: %s %s",
            e.code,
            e.description,
            extra=extra,
        )
        response = e.get_response()
        # Replace the body with JSON
        response.data = json.dumps({
            "error": e.description,
            "code": e.code,
            "request_id": req_id
        })
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Generic exception handler - logs full traceback and returns JSON."""
        tb = traceback.format_exc()
        req_id = (
            getattr(request, 'request_id', None)
            or request.environ.get('request_id')
        )
        extra = {"request_id": req_id}
        app.logger.exception(
            "Unhandled exception: %s",
            str(e),
            extra=extra,
        )
        payload = {"error": "Internal Server Error", "request_id": req_id}
        # In debug mode include exception details
        if app.config.get('DEBUG'):
            payload["exception"] = str(e)
            payload["traceback"] = tb
        return jsonify(payload), 500

    @app.errorhandler(404)
    def not_found_json(e):
        """Handle 404 errors with JSON response."""
        req_id = (
            getattr(request, 'request_id', None)
            or request.environ.get('request_id')
        )
        app.logger.warning(
            "404 Not Found: %s %s",
            request.method,
            request.path,
            extra={"request_id": req_id},
        )
        return jsonify({
            "error": "Not Found",
            "code": 404,
            "path": request.path,
            "request_id": req_id,
        }), 404


def add_json_error_converter(app):
    """Add after_request hook to convert HTML errors to JSON.

    Some servers/frameworks return HTML error pages; for API clients
    it's clearer to always return JSON payloads on errors.

    Args:
        app: Flask application instance
    """

    @app.after_request
    def ensure_json_errors(response):
        """Convert default HTML error pages into JSON for consistency."""
        try:
            html_ct = 'text/html; charset=utf-8'
            if response.status_code >= 400 and response.content_type == html_ct:
                req_id = (
                    getattr(request, 'request_id', None)
                    or request.environ.get('request_id')
                )
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

        return response


def setup_flask_app_hooks(app, log_dir='logs', enable_json_converter=True):
    """Complete setup of logging and hooks for a Flask app.

    This is a convenience function that calls all setup functions:
    - setup_app_logging
    - add_request_id_hooks
    - add_error_handlers
    - add_json_error_converter (optional)

    Args:
        app: Flask application instance
        log_dir: Directory to store log files (default: 'logs')
        enable_json_converter: Whether to enable HTML-to-JSON error conversion
    """
    setup_app_logging(app, log_dir=log_dir)
    add_request_id_hooks(app)
    add_error_handlers(app)
    if enable_json_converter:
        add_json_error_converter(app)
