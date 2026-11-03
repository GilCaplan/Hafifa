"""Runs before any test module, so it points the app at the test database and log before const.py reads them."""

import os

from tests.const import TEST_DATABASE_URL, TEST_LOG_FILE

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LOG_FILE"] = str(TEST_LOG_FILE)
TEST_LOG_FILE.unlink(missing_ok=True)
