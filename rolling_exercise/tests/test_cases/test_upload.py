"""POST /air-quality/upload"""

from pathlib import Path
from unittest.mock import patch

import psycopg
import pytest

from air_quality_api.const import Aqi, Columns, Tables
from air_quality_db.queries import count_rows
from tests.const import FILE_KEY, LINE_KEY, SAMPLE_FILES, Reading
from tests.utils import SAMPLE_READINGS, SAMPLE_SKIPPED_LINES, upload

FIRST_SAMPLE = SAMPLE_FILES[0]


def readings_of(path: Path) -> list[Reading]:
    return [reading for reading in SAMPLE_READINGS if reading[FILE_KEY] == path.name]


def count_alerts(readings: list[Reading]) -> int:
    return sum(reading[Columns.AQI] > Aqi.ALERT_THRESHOLD for reading in readings)


def test_each_sample_file_saves_its_valid_rows() -> None:
    for path in SAMPLE_FILES:
        readings = readings_of(path)
        response = upload(path.name, path.read_bytes())

        assert response.status_code == 200, path.name
        assert response.json() == {
            "filename": path.name,
            "inserted_rows": len(readings),
            "duplicate_rows": 0,
            "skipped_rows": SAMPLE_SKIPPED_LINES[path.name],
            "alerts": count_alerts(readings),
        }
    assert count_rows(Tables.READINGS) == len(SAMPLE_READINGS)
    assert count_rows(Tables.ALERTS) == count_alerts(SAMPLE_READINGS)


def test_column_names_ignore_case_spaces_and_extra_columns() -> None:
    _, *rows = FIRST_SAMPLE.read_text().splitlines()
    content = "\n".join([" Date , CITY ,pm2.5,no2,co2,notes", *(f"{row},extra" for row in rows)])

    assert upload(FIRST_SAMPLE.name, content).json()["inserted_rows"] == len(readings_of(FIRST_SAMPLE))


def test_uploading_a_file_again_skips_its_rows_as_duplicates() -> None:
    upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes())
    data = upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes()).json()

    assert (data["inserted_rows"], data["alerts"]) == (0, 0)
    assert data["duplicate_rows"] == len(readings_of(FIRST_SAMPLE))


def test_duplicates_are_logged_with_their_lines(caplog: pytest.LogCaptureFixture) -> None:
    first = readings_of(FIRST_SAMPLE)[0]
    upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes())
    with caplog.at_level("WARNING"):
        upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes())

    message = (
        f"Skipped line {first[LINE_KEY]} in {FIRST_SAMPLE.name}: "
        f"{first[Columns.CITY]} on {first[Columns.DATE]} is already saved"
    )
    assert message in caplog.messages


def test_duplicate_rows_within_one_file_are_saved_once() -> None:
    header, *rows = FIRST_SAMPLE.read_text().splitlines()
    readings = readings_of(FIRST_SAMPLE)
    data = upload(FIRST_SAMPLE.name, "\n".join([header, *rows, *rows])).json()

    assert (data["inserted_rows"], data["duplicate_rows"]) == (len(readings), len(readings))
    assert count_rows(Tables.ALERTS) == count_alerts(readings)


def test_non_csv_file_is_rejected() -> None:
    response = upload(f"{FIRST_SAMPLE.stem}.txt", FIRST_SAMPLE.read_bytes())

    assert response.status_code == 400
    assert "not a CSV file" in response.json()["detail"]


def test_file_missing_columns_is_rejected() -> None:
    content = "\n".join(",".join(line.split(",")[:3]) for line in FIRST_SAMPLE.read_text().splitlines())
    response = upload(FIRST_SAMPLE.name, content)

    assert response.status_code == 400
    assert "Missing columns: ['no2', 'co2']" in response.json()["detail"]


def test_empty_file_is_skipped() -> None:
    response = upload("empty.csv", "")

    assert response.status_code == 200
    assert response.json()["reason"] == "file is empty"


def test_database_unavailable_returns_503() -> None:
    with patch("air_quality_db.queries.get_connection", side_effect=psycopg.OperationalError("connection refused")):
        response = upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes())

    assert response.status_code == 503


@pytest.mark.usefixtures("load_samples")
def test_uploading_the_samples_twice_adds_nothing() -> None:
    second_round = [upload(path.name, path.read_bytes()).json() for path in SAMPLE_FILES]

    assert sum(data["inserted_rows"] for data in second_round) == 0
    assert count_rows(Tables.READINGS) == len(SAMPLE_READINGS)
