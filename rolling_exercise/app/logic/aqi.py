import logging

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.constants import ColumnSets
from app.db.models import Reading
from app.db.queries import fetch_rows, get_average_aqi
from app.logic.validation import validate_city
from app.schemas import AqiHistoryEntry, CityAverage
from calculate_aqi import calculate_aqi

logger = logging.getLogger(__name__)

# otypes lets it run on an empty DataFrame (an upload with no valid rows)
calculate_aqi_vectorized = np.vectorize(calculate_aqi, otypes=[float, object])


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pollutants = (df[column] for column in ColumnSets.POLLUTANTS)
    df[Reading.aqi.key], df[Reading.aqi_level.key] = calculate_aqi_vectorized(*pollutants)
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[Reading.aqi.key] > settings.aqi_alert_threshold, ColumnSets.ALERT]


def to_city_average(city: str, average: float) -> CityAverage:
    return CityAverage(city=city, average_aqi=round(average, settings.aqi_average_decimals))


def get_city_aqi_history(city: str) -> list[AqiHistoryEntry]:
    city = validate_city(city)
    history = [AqiHistoryEntry.model_validate(row) for row in fetch_rows(Reading, city=city, sort=Reading.date)]

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
