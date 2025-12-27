#!/usr/bin/env python3
"""Test runner that ensures clean exit after pytest completes.

This script uses os._exit() instead of sys.exit() to force immediate termination
without cleanup. This prevents hanging on background threads from OpenTelemetry,
FastAPI, SQLAlchemy connection pools, or other async resources.
"""
import os
import sys
import pytest

if __name__ == "__main__":
    # Build pytest arguments from command line args if provided
    # Otherwise use defaults optimized for CI/local testing
    args = sys.argv[1:] if len(sys.argv) > 1 else [
        "src/tests/",
        "-n", "auto",  # Parallel execution using all CPU cores
        "--tb=line",  # Compact traceback for faster output
        "--cov=src/app",
        "--cov-report=term-missing",
        "--durations=10",  # Show 10 slowest tests
    ]

    # Run pytest
    exit_code = pytest.main(args)

    # Force exit without cleanup to prevent hanging on background threads
    # This is necessary because OpenTelemetry and FastAPI may leave threads running
    os._exit(exit_code)
