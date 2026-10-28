"""
Constants for the tests. Don't import the app here: tests/__init__.py imports this file before the app is set up
for the tests.
"""

from pathlib import Path

# Paths
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
PYTEST_CONFIG = PROJECT_ROOT / "setup" / "pytest.ini"
SCHEMA_FILE = PROJECT_ROOT / "air_quality_db" / "schema.sql"
SAMPLE_FILES = sorted((PROJECT_ROOT / "air_quality_files" / "input").glob("*.csv"))
TEST_LOG_FILE = PROJECT_ROOT / "air_quality_files" / "logs" / "air_quality_test.log"  # emptied on every run

# Test database, created from the server's default database
SERVER_URL = "postgresql://localhost:5432"
TEST_DATABASE = "air_quality_test"
TEST_DATABASE_URL = f"{SERVER_URL}/{TEST_DATABASE}"
ADMIN_DATABASE_URL = f"{SERVER_URL}/postgres"

UPLOAD_PATH = "/air-quality/upload"
CSV_CONTENT_TYPE = "text/csv"

MISSING_VALUES = ("", "NaN")
FILE_KEY = "file"
LINE_KEY = "line"
Reading = dict[str, str | int | float]
