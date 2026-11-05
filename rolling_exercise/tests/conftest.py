import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = PROJECT_ROOT / "app" / "db" / "schema.sql"
TEST_LOG_FILE = PROJECT_ROOT / "air_quality_files" / "logs" / "air_quality_test.log"

SERVER_URL = "postgresql://localhost:5432"
TEST_DATABASE = "air_quality_test"
TEST_DATABASE_URL = f"{SERVER_URL}/{TEST_DATABASE}"
ADMIN_DATABASE_URL = f"{SERVER_URL}/postgres"

# Must come before the app imports: settings reads these when it's first imported
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LOG_FILE"] = str(TEST_LOG_FILE)
TEST_LOG_FILE.unlink(missing_ok=True)

from app.db.models import Alert, Reading  # noqa: E402
from app.support.config import settings  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Iterator[None]:
    assert settings.database_url == TEST_DATABASE_URL, f"The app isn't using the test database: {settings.database_url}"
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DATABASE}")

    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(SCHEMA_FILE.read_text())

    yield

    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE {TEST_DATABASE} WITH (FORCE)")


@pytest.fixture(autouse=True)
def empty_tables() -> None:
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(f"TRUNCATE {Alert.__tablename__}, {Reading.__tablename__} RESTART IDENTITY")
