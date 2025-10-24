import sys
from pathlib import Path

# Ensure Backend is importable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.app_factory import create_app


def test_models_endpoints():
    cfg = {
        "test_model": {
            "file_types": ["mp3"],
            "available_models": ["small", "large"],
        }
    }

    app = create_app()
    app.config["MODELS"] = cfg
    client = app.test_client()

    r = client.get("/models")
    assert r.status_code == 200
    data = r.get_json()
    assert "test_model" in data["models"]

    r2 = client.get("/models/test_model")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2["model"] == "test_model"

    r3 = client.get("/models/missing")
    assert r3.status_code == 404
