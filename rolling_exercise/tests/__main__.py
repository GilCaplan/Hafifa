"""
Runs every test file: python -m tests (from rolling_exercise/).
Extra arguments go to pytest, e.g. python -m tests -v, or python -m tests -k alerts to run only matching tests.
"""

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent

sys.exit(pytest.main([str(TESTS_DIR), *sys.argv[1:]]))
