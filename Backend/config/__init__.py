"""
Top-level package initializer for the `config` package.

This file exposes the `Config` class from `config.py` so older imports
like `from config import Config` continue to work.

This is a tiny compatibility shim used during local testing and CI smoke
runs. It intentionally does not change behavior of the original
`config/config.py` implementation.
"""
from .config import Config
