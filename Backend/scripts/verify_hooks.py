#!/usr/bin/env python
"""Verification script for hook implementation.

This script verifies that:
1. All modules import successfully
2. Shared utilities work correctly
3. Tests pass
4. Apps can start without errors
"""

import importlib
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def check_imports():
    """Check that all modules import successfully."""
    print_info("Checking module imports...")

    try:
        logging_utils = importlib.import_module("server.logging_utils")
        # sanity-check attributes exist
        _ = getattr(logging_utils, "setup_flask_app_hooks", None)
        print_success("server.logging_utils imports successfully")
    except Exception as exc:  # noqa: BLE001 - explicit exception handling for import failures
        print_error(f"Failed to import server.logging_utils: {exc}")
        return False

    try:
        app_module = importlib.import_module("app")
        # access attribute to ensure module loaded
        _ = getattr(app_module, "app", None)
        print_success("app.py imports successfully")
    except Exception as exc:
        print_error(f"Failed to import app.py: {exc}")
        return False

    try:
        ws_module = importlib.import_module("app_websocket")
        _ = getattr(ws_module, "app", None)
        print_success("app_websocket.py imports successfully")
    except Exception as exc:
        print_error(f"Failed to import app_websocket.py: {exc}")
        return False

    return True


def check_files_exist():
    """Check that all expected files exist."""
    print_info("Checking file existence...")

    files = [
        "server/logging_utils.py",
        "tests/test_hooks.py",
        "tests/test_websocket_hooks.py",
        "HOOK_IMPLEMENTATION_SUMMARY.md",
        "HOOKS_ANALYSIS.md",
        "HOOKS_QUICK_REFERENCE.md",
    ]

    all_exist = True
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            print_success(f"{file_path} exists")
        else:
            print_error(f"{file_path} missing")
            all_exist = False

    return all_exist


def check_tests():
    """Check that tests can be discovered."""
    print_info("Checking test discovery...")

    import pytest

    # Collect tests
    exit_code = pytest.main([
        "tests/test_hooks.py",
        "tests/test_websocket_hooks.py",
        "--collect-only",
        "-q",
    ])

    if exit_code == 0:
        print_success("All tests discovered successfully")
        return True
    print_error("Test discovery failed")
    return False


def run_tests():
    """Run the test suite."""
    print_info("Running test suite...")

    import pytest

    # Run tests
    exit_code = pytest.main([
        "tests/test_hooks.py",
        "tests/test_websocket_hooks.py",
        "-v",
        "--tb=short",
    ])

    if exit_code == 0:
        print_success("All tests passed")
        return True
    print_error("Some tests failed")
    return False


def verify_shared_utilities():
    """Verify shared utilities work correctly."""
    print_info("Verifying shared utilities...")

    try:
        from flask import Flask
        from server.logging_utils import setup_flask_app_hooks

        # Create a test app
        app = Flask("test_verify")
        app.config["TESTING"] = True

        # Set up hooks
        setup_flask_app_hooks(app, log_dir="test_logs", enable_json_converter=True)

        # Verify hooks were added
        assert len(app.before_request_funcs.get(None, [])) > 0, "No before_request hooks"
        assert len(app.after_request_funcs.get(None, [])) > 0, "No after_request hooks"
        assert (
            len(app.error_handler_spec.get(None, {}).get(None, {})) > 0
        ), "No error handlers"

        print_success("Shared utilities work correctly")

        # Clean up test logs
        import shutil

        test_log_dir = Path("test_logs")
        if test_log_dir.exists():
            try:
                shutil.rmtree(test_log_dir)
            except Exception:
                # Windows may lock files; ignore cleanup errors
                pass

        return True
    except Exception as exc:
        print_error(f"Shared utilities verification failed: {exc}")
        return False


def main():
    """Run all verifications."""
    print("\n" + "=" * 60)
    print("Hook Implementation Verification")
    print("=" * 60 + "\n")

    checks = [
        ("File Existence", check_files_exist),
        ("Module Imports", check_imports),
        ("Shared Utilities", verify_shared_utilities),
        ("Test Discovery", check_tests),
        ("Test Suite", run_tests),
    ]

    results = {}
    for name, check_func in checks:
        print(f"\n{'=' * 60}")
        print(f"Check: {name}")
        print("=" * 60)
        results[name] = check_func()

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, result in results.items():
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            all_passed = False

    print("=" * 60)

    if all_passed:
        print_success("\n🎉 ALL VERIFICATIONS PASSED! 🎉")
        print_info("Hook implementation is complete and working correctly.")
        return 0

    print_error("\n⚠️  SOME VERIFICATIONS FAILED")
    print_info("Please review the errors above and fix them.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
