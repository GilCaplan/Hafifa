"""
Runs every test file: python -m tests (from the project root).
Extra arguments go to pytest, e.g. python -m tests -v, or python -m tests -k alerts to run only matching tests.
"""

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
# pytest only finds pytest.ini on its own in the folder it runs from (or above), so point it at setup/
PYTEST_CONFIG = PROJECT_ROOT / "setup" / "pytest.ini"

sys.exit(pytest.main(["-c", str(PYTEST_CONFIG), "--rootdir", str(PROJECT_ROOT), str(TESTS_DIR), *sys.argv[1:]]))
