# test_resumable.py
# Minimal placeholder — tests for resumable uploads are optional in this cleanup batch
import pytest
from server.backend_skeleton import app, init_db


@pytest.fixture(scope="module")
def client():
    init_db()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_resumable_single_chunk(client):
    # create upload session
    rv = client.post("/uploads", json={"filename": "chunked.wav"})
    assert rv.status_code == 201
    upload = rv.get_json()
    upload_id = upload["upload_id"]

    # send single chunk
    data = b"fake-audio-bytes"
    rv = client.post(
        f"/uploads/{upload_id}/chunk",
        data=data,
        headers={"X-Chunk-Index": "0"},
    )
    assert rv.status_code == 204

    # complete upload
    rv = client.post(f"/uploads/{upload_id}/complete")
    assert rv.status_code == 201
    body = rv.get_json()
    assert "file_id" in body

    # download final file
    file_id = body["file_id"]
    rv = client.get(f"/download/{file_id}")
    assert rv.status_code == 200
    assert rv.data == data
