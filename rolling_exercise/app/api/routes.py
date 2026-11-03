from datetime import date

from fastapi import APIRouter, File, Query, UploadFile

from app.logic import alerts, aqi, readings, upload
from app.schemas import AlertResponse, AqiHistoryEntry, CityAverage, ReadingResponse, UploadSummary

router = APIRouter()


@router.post("/air-quality/upload")
def upload_air_quality_data(file: UploadFile = File(...)) -> UploadSummary:
    return upload.upload_air_quality_data(file)


@router.get("/air-quality")
def get_air_quality_data(start_date: date, end_date: date) -> list[ReadingResponse]:
    return readings.get_air_quality_data(start_date, end_date)


@router.get("/air-quality/city")
def get_air_quality_data_by_city(city: str) -> list[ReadingResponse]:
    return readings.get_air_quality_data_by_city(city)


@router.get("/aqi/history")
def get_city_aqi_history(city: str) -> list[AqiHistoryEntry]:
    return aqi.get_city_aqi_history(city)


@router.get("/aqi/average")
def get_city_aqi_average(city: str) -> CityAverage:
    return aqi.get_city_aqi_average(city)


@router.get("/aqi/best-cities")
def get_best_cities() -> list[CityAverage]:
    return aqi.get_best_cities()


@router.get("/alerts")
def get_all_alerts() -> list[AlertResponse]:
    return alerts.get_all_alerts()


@router.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")) -> list[AlertResponse]:
    return alerts.get_alerts_by_date(alert_date)


@router.get("/alerts/city")
def get_alerts_by_city(city: str) -> list[AlertResponse]:
    return alerts.get_alerts_by_city(city)
