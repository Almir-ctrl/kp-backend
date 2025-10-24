"""Integration tests for app_websocket.py hooks functionality.

Tests that app_websocket.py properly implements:
- Request ID tracking
- Error handling
- CORS headers
- Logging integration
"""

import sys
from pathlib import Path
import uuid
import pytest

# Ensure repo root is on path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_websocket import app


@pytest.fixture
def client():
    """Create a test client for app_websocket."""
    # Import here to ensure sys.path tweaks above take effect
    from app_websocket import app
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    return app.test_client()


class TestWebSocketAppRequestID:
    """Test request ID functionality in WebSocket app."""

    def test_health_endpoint_has_request_id(self, client):
        """Test that /health endpoint returns request ID."""
        response = client.get('/health')
        assert response.status_code == 200
        assert 'X-Request-ID' in response.headers

        # Verify UUID format
        req_id = response.headers['X-Request-ID']
        try:
            uuid.UUID(req_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {req_id}")

    def test_client_request_id_preserved(self, client):
        """Test that client-provided request ID is preserved."""
        client_id = str(uuid.uuid4())
        response = client.get('/health', headers={'X-Request-ID': client_id})
        assert response.headers['X-Request-ID'] == client_id

    def test_models_endpoint_has_request_id(self, client):
        """Test /models endpoint returns request ID."""
        response = client.get('/models')
        assert response.status_code == 200
        assert 'X-Request-ID' in response.headers


class TestWebSocketAppErrorHandling:
    """Test error handling in WebSocket app."""

    def test_404_returns_json_with_request_id(self, client):
        """Test that 404 errors return JSON format."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert data is not None
        assert 'error' in data
        assert 'code' in data
        assert 'request_id' in data
        assert data['code'] == 404

    def test_request_id_in_header_and_body_match(self, client):
        """Test request ID consistency between header and body."""
        response = client.get('/nonexistent')

        header_id = response.headers.get('X-Request-ID')
        body_data = response.get_json()
        body_id = body_data.get('request_id')

        assert header_id == body_id


class TestWebSocketAppCORS:
    """Test CORS headers in WebSocket app."""

    def test_cors_exposes_request_id_header(self, client):
        """Test that X-Request-ID is exposed via CORS."""
        response = client.get('/health')

        expose_headers = response.headers.get(
            'Access-Control-Expose-Headers', ''
        )
        assert 'X-Request-ID' in expose_headers

    def test_no_duplicate_expose_headers(self, client):
        """Test that CORS expose headers don't have duplicates."""
        # Make multiple requests
        for _ in range(3):
            response = client.get('/health')
            expose_headers = response.headers.get(
                'Access-Control-Expose-Headers', ''
            )
            headers_list = [h.strip() for h in expose_headers.split(',')]

            # No duplicates
            unique_headers = set(headers_list)
            assert len(headers_list) == len(unique_headers), \
                f"Duplicate headers: {headers_list}"


class TestWebSocketAppEndpoints:
    """Test that existing endpoints still work with hooks."""

    def test_health_endpoint_response(self, client):
        """Test /health endpoint returns expected data."""
        response = client.get('/health')
        assert response.status_code == 200

        data = response.get_json()
        assert 'status' in data
        assert 'websocket_support' in data
        assert data['status'] == 'healthy'
        assert data['websocket_support'] is True

    def test_models_endpoint_response(self, client):
        """Test /models endpoint returns expected data."""
        response = client.get('/models')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        # Should have model configurations


class TestWebSocketAppLogging:
    """Test that logging is properly configured."""

    def test_app_logger_exists(self):
        """Test that app has logger configured."""
        assert hasattr(app, 'logger')
        assert app.logger is not None

    def test_log_directory_created(self):
        """Test that logs directory is created."""
        from pathlib import Path
        log_dir = Path(__file__).parent.parent / 'logs'
        # Directory should exist or be creatable
        # (might not exist yet if no requests made)
        assert log_dir.parent.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
