"""Fixed SQL statements used by queries.py. Their placeholders are filled from Columns.READING and Columns.ALERT."""

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
