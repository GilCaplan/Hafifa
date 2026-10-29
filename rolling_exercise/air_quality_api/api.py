from datetime import date

from fastapi import FastAPI, File, Query, UploadFile

from air_quality_api import logic
from air_quality_api.handlers import register_handlers
from air_quality_api.logs import setup_logging

setup_logging()

app = FastAPI()
register_handlers(app)  # logging and error responses around every request


@app.post("/air-quality/upload")
def upload_air_quality_data(file: UploadFile = File(...)):  # noqa: B008
    return logic.upload_air_quality_data(file)


@app.get("/air-quality")
def get_air_quality_data(start_date: date, end_date: date):
    return logic.get_air_quality_data(start_date, end_date)


@app.get("/air-quality/city")
def get_air_quality_data_by_city(city: str):
    return logic.get_air_quality_data_by_city(city)


@app.get("/aqi/history")
def get_city_aqi_history(city: str):
    return logic.get_city_aqi_history(city)


@app.get("/aqi/average")
def get_city_aqi_average(city: str):
    return logic.get_city_aqi_average(city)


@app.get("/aqi/best-cities")
def get_best_cities():
    return logic.get_best_cities()


@app.get("/alerts")
def get_all_alerts():
    return logic.get_all_alerts()


@app.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")):  # noqa: B008
    return logic.get_alerts_by_date(alert_date)


@app.get("/alerts/city")
def get_alerts_by_city(city: str):
    return logic.get_alerts_by_city(city)
