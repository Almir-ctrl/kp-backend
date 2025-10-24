# Waitress configuration for Windows production
import os

# Server settings
host = "0.0.0.0"
port = int(os.environ.get("PORT", 8000))
threads = 4
connection_limit = 1000
cleanup_interval = 30
channel_timeout = 120
