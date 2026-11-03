from collections.abc import Iterator

import psycopg
import pytest

from app.core.config import settings
from app.db.models import Alert, Reading
from tests.const import ADMIN_DATABASE_URL, SCHEMA_FILE, TEST_DATABASE, TEST_DATABASE_URL


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
