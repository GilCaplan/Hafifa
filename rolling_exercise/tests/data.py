"""Rows for the basic tests, and known facts about the sample files in air_quality_files/input/."""

from pathlib import Path

from calculate_aqi import calculate_aqi

# Basic test rows: (date, city, pm25, no2, co2)
HAIFA_20 = ("2024-11-20", "Haifa", 10, 20, 4)  # Good
HAIFA_21 = ("2024-11-21", "Haifa", 40, 60, 12)  # Unhealthy for Sensitive Groups
ARAD_20 = ("2024-11-20", "Arad", 5, 10, 2)  # Good, the cleanest
TEL_AVIV_20 = ("2024-11-20", "Tel Aviv", 20, 30, 6)  # Moderate
EILAT_20 = ("2024-11-20", "Eilat", 300, 20, 4)  # Hazardous: AQI over 300, so an alert


def aqi_of(row: tuple) -> float:
    """The AQI the given calculate_aqi function gives a basic test row."""
    _, _, pm25, no2, co2 = row
    return calculate_aqi(pm25, no2, co2)[0]


# Sample files (air_quality_files/input/). Every valid sample reading has CO2 around 400, above the top of
# calculate_aqi's CO2 scale (200), so every one scores AQI 500 and is also an alert.
# Rows with an empty value or the text NaN are skipped.
SAMPLE_FILES = sorted((Path(__file__).resolve().parent.parent / "air_quality_files" / "input").glob("*.csv"))
SAMPLE_SKIPPED_LINES = {
    "air_quality_2024-11-24.csv": [],
    "air_quality_2024-11-25.csv": [],
    "air_quality_2024_11_19.csv": [8],
    "air_quality_2024_11_20.csv": [],
    "air_quality_2024_11_21.csv": [5, 7],
    "air_quality_2024_11_22.csv": [5, 8],
    "air_quality_2024_11_23.csv": [6],
}
SAMPLE_READINGS_PER_DATE = {
    "2024-11-19": 6,
    "2024-11-20": 7,
    "2024-11-21": 5,
    "2024-11-22": 5,
    "2024-11-23": 6,
    "2024-11-24": 6,
    "2024-11-25": 7,
}
SAMPLE_READINGS_PER_CITY = {
    "Ganei Tikva": 6,
    "Hod Hasharon": 5,
    "Kefar Sava": 6,
    "Netanya": 7,
    "Rishon LeTsiyon": 5,
    "Tel Mond": 6,
    "Tzur Moshe": 7,
}
SAMPLE_TOTAL_READINGS = sum(SAMPLE_READINGS_PER_DATE.values())
SAMPLE_FIRST_DATE, SAMPLE_LAST_DATE = min(SAMPLE_READINGS_PER_DATE), max(SAMPLE_READINGS_PER_DATE)
SAMPLE_AQI = 500.0
