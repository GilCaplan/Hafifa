"""The database tables as SQLAlchemy models. schema.sql creates the tables and their constraints: keep them in sync."""

import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Reading(Base):
    """One city's air quality on one day, with its calculated AQI."""

    __tablename__ = "air_quality_readings"
    __table_args__ = (UniqueConstraint("date", "city"),)  # the uploads' ON CONFLICT (date, city) relies on it

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date]
    city: Mapped[str]
    pm25: Mapped[float]
    no2: Mapped[float]
    co2: Mapped[float]
    aqi: Mapped[float]
    aqi_level: Mapped[str]


class Alert(Base):
    """A reading with an AQI over the alert threshold."""

    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("date", "city"),)  # the uploads' ON CONFLICT (date, city) relies on it

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date]
    city: Mapped[str]
    aqi: Mapped[float]


Table = type[Reading] | type[Alert]  # what the query functions accept as `table`
