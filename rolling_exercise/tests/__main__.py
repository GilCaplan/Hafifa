"""
Runs every test file: python -m tests (from the project root).
Extra arguments go to pytest, e.g. python -m tests -v, or python -m tests -k alerts to run only matching tests.
"""

import sys

import pytest

from tests.const import PROJECT_ROOT, PYTEST_CONFIG, TESTS_DIR

# pytest only finds pytest.ini on its own in the folder it runs from (or above), so point it at setup/
sys.exit(pytest.main(["-c", str(PYTEST_CONFIG), "--rootdir", str(PROJECT_ROOT), str(TESTS_DIR), *sys.argv[1:]]))
