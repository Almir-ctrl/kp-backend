"""RQ worker entrypoint for background jobs.

Usage (development):
  # start redis locally (e.g., docker run -p 6379:6379 redis)
  export REDIS_URL=redis://localhost:6379
  python server/worker.py

This file registers a simple task that calls into backend_skeleton.background_process.
"""
import os
from rq import Worker, Queue, Connection
from redis import Redis

from server.backend_skeleton import background_process


def enqueue_job(redis_url, job_id, file_id, model):
    r = Redis.from_url(redis_url)
    q = Queue("default", connection=r)
    # enqueue a wrapper task
    q.enqueue_call(func=background_process, args=(job_id, file_id, model))


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_conn = Redis.from_url(redis_url)
    with Connection(redis_conn):
        worker = Worker(["default"])
        worker.work()


if __name__ == "__main__":
    main()
