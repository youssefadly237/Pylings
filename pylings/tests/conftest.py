"""Pytest configuration for Pylings tests.

This file is automatically loaded by pytest and configures the test environment.
"""
import sys
from pathlib import Path

tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))
