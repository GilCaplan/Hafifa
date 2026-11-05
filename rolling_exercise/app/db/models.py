"""schema.sql creates these tables and their constraints: keep the two in sync."""

import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Reading(Base):
    __tablename__ = "air_quality_readings"
    __table_args__ = (UniqueConstraint("date", "city"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date]
    city: Mapped[str]
    pm25: Mapped[float]
    no2: Mapped[float]
    co2: Mapped[float]
    aqi: Mapped[float]
    aqi_level: Mapped[str]


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("date", "city"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date]
    city: Mapped[str]
    aqi: Mapped[float]


Table = type[Reading] | type[Alert]
