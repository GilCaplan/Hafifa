"""Fixed SQL statements used by queries.py, and the DataFrame columns that fill their placeholders."""

from air_quality_api.const import (
    AQI_COLUMN,
    AQI_LEVEL_COLUMN,
    CITY_COLUMN,
    CO2_COLUMN,
    DATE_COLUMN,
    NO2_COLUMN,
    PM25_COLUMN,
)

INSERT_READING = """
    INSERT INTO air_quality_readings (date, city, pm25, no2, co2, aqi, aqi_level)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (date, city) DO NOTHING
    RETURNING date, city
"""

INSERT_ALERT = """
    INSERT INTO alerts (date, city, aqi)
    VALUES (%s, %s, %s)
    ON CONFLICT (date, city) DO NOTHING
"""

# Same order as the columns in INSERT_READING / INSERT_ALERT: each %s is filled from these, in this order
READING_COLUMNS = [DATE_COLUMN, CITY_COLUMN, PM25_COLUMN, NO2_COLUMN, CO2_COLUMN, AQI_COLUMN, AQI_LEVEL_COLUMN]
ALERT_COLUMNS = [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN]
