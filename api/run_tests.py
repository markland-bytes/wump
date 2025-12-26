#!/usr/bin/env python3
"""Test runner that ensures clean exit after pytest completes."""
import os
import sys
import pytest

if __name__ == "__main__":
    # Run pytest with command line arguments
    exit_code = pytest.main([
        "src/tests/",
        "-v",
        "--tb=short",
        "--cov=src/app",
        "--cov-report=term-missing",
    ])

    # Force exit without cleanup to prevent hanging on background threads
    # This is necessary because OpenTelemetry and FastAPI may leave threads running
    os._exit(exit_code)
