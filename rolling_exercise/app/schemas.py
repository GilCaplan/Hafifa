import datetime

from pydantic import BaseModel


class UploadSummary(BaseModel):
    filename: str | None
    inserted_rows: int = 0
    duplicate_rows: int = 0
    skipped_rows: list[int] = []
    alerts: int = 0
    # Why an upload saved nothing, e.g. an empty file
    reason: str | None = None


class CityAverage(BaseModel):
    city: str
    average_aqi: float


class AqiHistoryEntry(BaseModel):
    date: datetime.date
    city: str
    aqi: float
    aqi_level: str


class ReadingResponse(AqiHistoryEntry):
    id: int
    pm25: float
    no2: float
    co2: float


class AlertResponse(BaseModel):
    id: int
    date: datetime.date
    city: str
    aqi: float
