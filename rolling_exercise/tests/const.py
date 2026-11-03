"""Don't import the app here: tests/__init__.py imports this file before the app is set up for the tests."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = PROJECT_ROOT / "app" / "db" / "schema.sql"
TEST_LOG_FILE = PROJECT_ROOT / "air_quality_files" / "logs" / "air_quality_test.log"

SERVER_URL = "postgresql://localhost:5432"
TEST_DATABASE = "air_quality_test"
TEST_DATABASE_URL = f"{SERVER_URL}/{TEST_DATABASE}"
ADMIN_DATABASE_URL = f"{SERVER_URL}/postgres"
