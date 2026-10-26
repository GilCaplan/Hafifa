"""Fixed SQL statements used by queries.py, and the DataFrame columns that fill their placeholders."""

from air_quality_api.const import Columns

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

# Fill the %s placeholders above, in order
READING_COLUMNS = [Columns.DATE, Columns.CITY, Columns.PM25, Columns.NO2, Columns.CO2, Columns.AQI, Columns.AQI_LEVEL]
ALERT_COLUMNS = [Columns.DATE, Columns.CITY, Columns.AQI]
