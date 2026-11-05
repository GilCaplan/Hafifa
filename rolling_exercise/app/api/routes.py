import logging
from datetime import date

from fastapi import APIRouter, File, Query, UploadFile

from app.controllers import alerts, aqi, readings, upload
from app.schemas import AlertResponse, AqiHistoryEntry, CityAverage, ReadingResponse, UploadSummary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/air-quality/upload")
def upload_air_quality_data(file: UploadFile = File(...)) -> UploadSummary:
    logger.info(f"Received a request to upload air quality data from file {file.filename}")
    return upload.upload_air_quality_data(file)


@router.get("/air-quality")
def get_air_quality_data(start_date: date, end_date: date) -> list[ReadingResponse]:
    logger.info(f"Received a request to get air quality data from {start_date} to {end_date}")
    return readings.get_air_quality_data(start_date, end_date)


@router.get("/air-quality/city")
def get_air_quality_data_by_city(city: str) -> list[ReadingResponse]:
    logger.info(f"Received a request to get air quality data for city {city}")
    return readings.get_air_quality_data_by_city(city)


@router.get("/aqi/history")
def get_city_aqi_history(city: str) -> list[AqiHistoryEntry]:
    logger.info(f"Received a request to get the AQI history of city {city}")
    return aqi.get_city_aqi_history(city)


@router.get("/aqi/average")
def get_city_aqi_average(city: str) -> CityAverage:
    logger.info(f"Received a request to get the AQI average of city {city}")
    return aqi.get_city_aqi_average(city)


@router.get("/aqi/best-cities")
def get_best_cities() -> list[CityAverage]:
    logger.info("Received a request to get the best cities")
    return aqi.get_best_cities()


@router.get("/alerts")
def get_all_alerts() -> list[AlertResponse]:
    logger.info("Received a request to get all alerts")
    return alerts.get_all_alerts()


@router.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")) -> list[AlertResponse]:
    logger.info(f"Received a request to get the alerts from date {alert_date}")
    return alerts.get_alerts_by_date(alert_date)


@router.get("/alerts/city")
def get_alerts_by_city(city: str) -> list[AlertResponse]:
    logger.info(f"Received a request to get the alerts for city {city}")
    return alerts.get_alerts_by_city(city)
