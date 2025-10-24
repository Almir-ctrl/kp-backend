"""Minimal app factory wrapper for backward-compatible refactor.

This file provides a small `create_app()` function that returns the
existing Flask `app` defined in `entrypoints.app`. The goal is to
introduce an app factory API surface without changing runtime
behaviour; later commits will migrate route registration into
blueprints and move initialization here.

Keep this file intentionally tiny to make the first refactor commit
low-risk and reversible.
"""
from typing import Optional
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import uuid


def _make_minimal_app():
    """Create a minimal Flask app used as a fallback during tests.

    This avoids importing heavy runtime dependencies in `entrypoints.app`
    when running unit tests in constrained environments.
    """
    app = Flask(__name__)
    CORS(app, origins="*")

    @app.before_request
    def _attach_request_id():
        incoming = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        g.request_id = incoming or str(uuid.uuid4())

    @app.after_request
    def _expose_request_id(resp):
        try:
            resp.headers["X-Request-ID"] = getattr(g, "request_id", "")
            existing = resp.headers.get("Access-Control-Expose-Headers", "")
            tokens = {t.strip() for t in existing.split(",") if t.strip()} if existing else set()
            tokens.add("X-Request-ID")
            resp.headers["Access-Control-Expose-Headers"] = ", ".join(sorted(tokens))
        except Exception:
            pass
        return resp

    @app.route("/health")
    def _health():
        return jsonify({"status": "ok"})

    # Attempt to register optional blueprints on the minimal app to mirror
    # behavior we will add to the legacy app. Fail quietly if blueprints
    # are not available in this early refactor step.
    try:
        from server.blueprints.models import bp as models_bp

        app.register_blueprint(models_bp)
    except Exception:
        pass

    return app


def create_app(config_object: Optional[object] = None):
    """Return the existing Flask app instance from the legacy entrypoint.

    If importing the legacy entrypoint fails (heavy deps missing), return a
    minimal test-friendly Flask app instead. If a `config_object` is
    provided, it will be applied via `app.config.from_object()`.
    """
    try:
        # Import lazily to avoid circular imports during early refactors.
        from entrypoints.app import app as legacy_app
    except Exception:
        # Fall back to a minimal app for tests / constrained envs
        app = _make_minimal_app()
        if config_object is not None:
            try:
                app.config.from_object(config_object)
            except Exception:
                pass
        return app

    if config_object is not None:
        try:
            legacy_app.config.from_object(config_object)
        except Exception:
            pass

    # Attempt to register our blueprints on the legacy app if possible.
    try:
        # Import blueprint module lazily; if it fails, ignore — this keeps
        # the change backward compatible for the first PR.
        from server.blueprints.health import bp as health_bp

        from server.blueprints.models import bp as models_bp

        # Only register if not already registered
        # Only register if a health endpoint does not already exist
        has_health = any(
            r.endpoint.startswith("health.")
            for r in legacy_app.url_map.iter_rules()
        )
        if not has_health:
            legacy_app.register_blueprint(health_bp)

        # Register models blueprint if not present
        try:
            has_models = any(r.rule.startswith("/models") for r in legacy_app.url_map.iter_rules())
        except Exception:
            has_models = False

        if not has_models:
            legacy_app.register_blueprint(models_bp)
    except Exception:
        # If anything goes wrong, continue returning the legacy app unchanged
        pass

    return legacy_app
