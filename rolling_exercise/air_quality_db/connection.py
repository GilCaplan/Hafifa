import psycopg

from air_quality_api.const import settings


def get_connection() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)
