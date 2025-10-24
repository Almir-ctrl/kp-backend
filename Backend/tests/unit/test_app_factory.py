import sys
from pathlib import Path


def test_create_app_importable():
    # Ensure the Backend package is importable by adding it to sys.path.
    repo_root = Path(__file__).resolve().parents[3]
    backend_dir = repo_root / "Backend"
    sys.path.insert(0, str(backend_dir))

    from server.app_factory import create_app

    app = create_app()
    # Basic assertions about the Flask app object
    assert app is not None
    assert hasattr(app, "wsgi_app")
    # Ensure after_request functions mapping exists
    funcs = getattr(app, "after_request_funcs", None)
    assert funcs is not None
