# Gunicorn configuration for production
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 300  # 5 minutes for audio processing
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
