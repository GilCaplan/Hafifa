from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import Session

from air_quality_api.const import settings

# DATABASE_URL is a plain postgresql:// URL; tell SQLAlchemy to use the psycopg (version 3) driver
engine = create_engine(make_url(settings.database_url).set(drivername="postgresql+psycopg"))


def get_session() -> Session:
    return Session(engine)
