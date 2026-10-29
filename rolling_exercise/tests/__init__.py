"""
Points the app at the test database and a fresh test log file. Python runs this once, before any module in tests/
(conftest.py included), so it happens before the app's const.py reads these settings and opens the log.
"""

import os

from tests.const import TEST_DATABASE_URL, TEST_LOG_FILE

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LOG_FILE"] = str(TEST_LOG_FILE)
TEST_LOG_FILE.unlink(missing_ok=True)
