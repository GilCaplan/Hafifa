"""
Shared test setup.

Tests run against their own PostgreSQL database (air_quality_test by default), created from air_quality_db/schema.sql
at the start of the session and dropped at the end, so they never touch the real database. Every test starts with
empty tables.

Settings (environment variables, all optional):
    TEST_ADMIN_DATABASE_URL: a database on the server to create the test database from
                             (default postgresql://localhost:5432/postgres, as the current OS user)
    TEST_DATABASE: the test database's name (default air_quality_test)
"""

import os
import tempfile
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = PROJECT_ROOT / "air_quality_db" / "schema.sql"

ADMIN_DATABASE_URL = os.getenv("TEST_ADMIN_DATABASE_URL", "postgresql://localhost:5432/postgres")
TEST_DATABASE = os.getenv("TEST_DATABASE", "air_quality_test")
TEST_DATABASE_URL = f"{ADMIN_DATABASE_URL.rsplit('/', 1)[0]}/{TEST_DATABASE}"

# Set before the app is imported: const.py reads these at import time, and values from .env never override them.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LOG_FILE"] = str(Path(tempfile.gettempdir()) / "air_quality_test.log")


def drop_test_database(admin: psycopg.Connection) -> None:
    admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(TEST_DATABASE)))


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        drop_test_database(admin)
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE)))
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
        connection.execute(SCHEMA_FILE.read_text())
    yield
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        drop_test_database(admin)


@pytest.fixture(autouse=True)
def empty_tables():
    from air_quality_api.const import ALERTS_TABLE, READINGS_TABLE

    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            sql.SQL("TRUNCATE {}, {} RESTART IDENTITY").format(
                sql.Identifier(ALERTS_TABLE), sql.Identifier(READINGS_TABLE)
            )
        )


@pytest.fixture(scope="session")
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def upload(client):
    """Uploads a file: upload(name, content) -> response."""

    def upload_file(name: str, content: str | bytes):
        return client.post("/air-quality/upload", files={"file": (name, content, "text/csv")})

    return upload_file


@pytest.fixture
def upload_rows(upload):
    """Uploads a CSV made from (date, city, pm25, no2, co2) tuples: upload_rows(row, row, ...) -> response."""

    def upload_csv(*rows: tuple):
        lines = ["date,city,PM2.5,NO2,CO2", *(",".join(map(str, row)) for row in rows)]
        return upload("readings.csv", "\n".join(lines))

    return upload_csv


@pytest.fixture
def load_samples(upload):
    """Uploads every sample file in air_quality_files/ and returns {file name: response}."""
    from tests.data import SAMPLE_FILES

    return {path.name: upload(path.name, path.read_bytes()) for path in SAMPLE_FILES}
