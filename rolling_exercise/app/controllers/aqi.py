import logging

import numpy as np
import pandas as pd

from app.controllers.validation import validate_city
from app.db.models import Reading
from app.db.queries import fetch_rows, get_average_aqi
from app.schemas import AqiHistoryEntry, CityAverage
from app.support.config import settings
from app.support.constants import ColumnSets
from calculate_aqi import calculate_aqi

logger = logging.getLogger(__name__)


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    calculate = np.vectorize(calculate_aqi, otypes=[float, object])
    df[Reading.aqi.key], df[Reading.aqi_level.key] = calculate(*df[ColumnSets.POLLUTANTS].to_numpy().T)
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[Reading.aqi.key] > settings.aqi_alert_threshold, ColumnSets.ALERT]


def to_city_average(city: str, average: float) -> CityAverage:
    return CityAverage(city=city, average_aqi=round(average, settings.aqi_average_decimals))


def get_city_aqi_history(city: str) -> list[AqiHistoryEntry]:
    city = validate_city(city)
    history = [
        AqiHistoryEntry.model_validate(city_data) for city_data in fetch_rows(Reading, city=city, sort=Reading.date)
    ]

    logger.info(f"Found {len(history)} days of AQI history for {city}")
    return history


def get_city_aqi_average(city: str) -> CityAverage:
    city = validate_city(city)
    average = to_city_average(city, get_average_aqi([city])[city])

    logger.info(f"Average AQI for {city}: {average.average_aqi}")
    return average


def get_best_cities() -> list[CityAverage]:
    averages = get_average_aqi(limit=settings.best_cities_count)
    best = [to_city_average(city, average) for city, average in averages.items()]

    logger.info(f"Best cities: {', '.join(f'{average.city} ({average.average_aqi})' for average in best)}")
    return best
