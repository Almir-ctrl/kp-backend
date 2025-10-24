# Gunicorn Configuration for Production
# Optimized for AI model backend with WebSocket support

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"  # Required for SocketIO
worker_connections = 1000
timeout = 300  # 5 minutes for AI processing
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Process naming
proc_name = "ai-backend-gunicorn"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (handled by nginx in production)
# keyfile = None
# certfile = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True  # Load app before forking workers
enable_stdio_inheritance = True

# Restart workers after this many requests (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("🚀 AI Backend Server is ready for production!")
    server.log.info(f"🌐 Listening on {bind}")
    server.log.info(f"👥 Workers: {workers}")
    server.log.info(f"⚡ Worker class: {worker_class}")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} ready for requests")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGABRT signal")
