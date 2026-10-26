"""Helpers for the tests: the API client, uploading a file, and the readings expected from the sample files."""

import csv
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response

from air_quality_api.api import app
from air_quality_api.const import Columns, Validation
from calculate_aqi import calculate_aqi
from tests.const import (
    CSV_CONTENT_TYPE,
    FILE_KEY,
    LINE_KEY,
    MISSING_VALUES,
    SAMPLE_FILES,
    UPLOAD_PATH,
    Reading,
)

client = TestClient(app)


def upload(name: str, content: str | bytes) -> Response:
    return client.post(UPLOAD_PATH, files={"file": (name, content, CSV_CONTENT_TYPE)})


def read_sample_file(path: Path) -> tuple[list[Reading], list[int]]:
    """A sample file's valid rows with their AQI, and the line numbers of rows with an empty or NaN value."""
    readings: list[Reading] = []
    skipped_lines: list[int] = []
    with path.open() as file:
        reader = csv.DictReader(file)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]  # the app's column names
        for line, row in enumerate(reader, start=Validation.CSV_HEADER_LINES + 1):
            if any(value in MISSING_VALUES for value in row.values()):
                skipped_lines.append(line)
                continue
            aqi, aqi_level = calculate_aqi(*(float(row[column]) for column in Columns.POLLUTANTS))
            reading = {
                FILE_KEY: path.name,
                LINE_KEY: line,
                Columns.DATE: row[Columns.DATE],
                Columns.CITY: row[Columns.CITY],
                Columns.AQI: aqi,
                Columns.AQI_LEVEL: aqi_level,
            }
            readings.append(reading)
    return readings, skipped_lines


SAMPLE_READINGS: list[Reading] = [reading for path in SAMPLE_FILES for reading in read_sample_file(path)[0]]
SAMPLE_SKIPPED_LINES: dict[str, list[int]] = {path.name: read_sample_file(path)[1] for path in SAMPLE_FILES}
