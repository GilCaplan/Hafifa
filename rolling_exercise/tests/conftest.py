"""
Runs around the tests: creates the test database (see tests/__init__.py) for the run and drops it at the end,
empties its tables before every test, and uploads the sample files for the tests that ask for them.
"""

from collections.abc import Iterator

import psycopg
import pytest

from air_quality_api.const import settings
from air_quality_db.models import Alert, Reading
from tests.const import (
    ADMIN_DATABASE_URL,
    SAMPLE_FILES,
    SCHEMA_FILE,
    TEST_DATABASE,
    TEST_DATABASE_URL,
)
from tests.utils import upload


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Iterator[None]:
    assert settings.database_url == TEST_DATABASE_URL, f"The app isn't using the test database: {settings.database_url}"
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DATABASE}")
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(SCHEMA_FILE.read_text())
    yield
    # run all tests then continue
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE {TEST_DATABASE} WITH (FORCE)")


@pytest.fixture(autouse=True)
def empty_tables() -> None:
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(f"TRUNCATE {Alert.__tablename__}, {Reading.__tablename__} RESTART IDENTITY")


@pytest.fixture
def load_samples() -> None:
    """Uploads every sample file. Use with @pytest.mark.usefixtures("load_samples")."""
    for path in SAMPLE_FILES:
        upload(path.name, path.read_bytes())
