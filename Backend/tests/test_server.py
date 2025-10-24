#!/usr/bin/env python3
# Simple test server to verify the /status endpoint works
#
# This tiny module is intentionally minimal and used for quick local
# checks of the backend health/status endpoints.
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Keep CORS line short to satisfy linters
CORS(
    app,
    origins="*",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
)


@app.route('/status', methods=['GET'])
def status():
    """Simple status endpoint for frontend connection testing."""
    return jsonify({'status': 'ok'})


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'Test server is running'})


if __name__ == '__main__':
    print("Starting test server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
