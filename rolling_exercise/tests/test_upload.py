"""POST /air-quality/upload"""

from unittest.mock import patch

import psycopg
import pytest

from air_quality_api.const import ALERTS_TABLE, READINGS_TABLE
from air_quality_db.queries import count_rows
from tests.data import EILAT_20, HAIFA_20, SAMPLE_FILES, SAMPLE_SKIPPED_LINES, SAMPLE_TOTAL_READINGS

# Basic


def test_valid_rows_are_saved_and_alerts_counted(upload_rows):
    response = upload_rows(HAIFA_20, EILAT_20)

    assert response.status_code == 200
    assert response.json() == {
        "filename": "readings.csv",
        "inserted_rows": 2,
        "duplicate_rows": 0,
        "skipped_rows": [],
        "alerts": 1,
    }
    assert count_rows(READINGS_TABLE) == 2
    assert count_rows(ALERTS_TABLE) == 1


def test_rows_with_missing_or_invalid_values_are_skipped(upload):
    content = "\n".join(
        [
            "date,city,PM2.5,NO2,CO2",
            "2024-11-20,Haifa,10,20,4",  # line 2: valid
            "2024-11-20,Arad,abc,20,4",  # line 3: not a number
            "2024-13-45,Eilat,10,20,4",  # line 4: not a date
            "2024-11-20,Netanya,10,,4",  # line 5: missing value
            "2024-11-20,Ashdod,-5,20,4",  # line 6: negative
            "2024-11-20,Holon,10,20,NaN",  # line 7: NaN
        ]
    )
    data = upload("readings.csv", content).json()

    assert data["inserted_rows"] == 1
    assert data["skipped_rows"] == [3, 4, 5, 6, 7]


def test_column_names_ignore_case_spaces_and_extra_columns(upload):
    content = " Date , CITY ,pm2.5,no2,co2,notes\n2024-11-20,Haifa,10,20,4,hello"

    assert upload("readings.csv", content).json()["inserted_rows"] == 1


def test_uploading_the_same_rows_again_skips_them_as_duplicates(upload_rows):
    upload_rows(HAIFA_20, EILAT_20)
    data = upload_rows(HAIFA_20, EILAT_20).json()

    assert data["inserted_rows"] == 0
    assert data["duplicate_rows"] == 2
    assert data["alerts"] == 0


def test_duplicates_are_logged_with_their_lines(upload_rows, caplog):
    upload_rows(HAIFA_20)
    with caplog.at_level("WARNING"):
        upload_rows(EILAT_20, HAIFA_20)  # Haifa is line 3 of this upload

    assert "Skipped line 3 in readings.csv: Haifa on 2024-11-20 is already saved" in caplog.messages


def test_duplicate_within_one_file_is_saved_once(upload_rows):
    data = upload_rows(EILAT_20, EILAT_20).json()

    assert (data["inserted_rows"], data["duplicate_rows"], data["alerts"]) == (1, 1, 1)
    assert count_rows(ALERTS_TABLE) == 1


def test_non_csv_file_is_rejected(upload):
    response = upload("notes.txt", "hello")

    assert response.status_code == 400
    assert "not a CSV file" in response.json()["detail"]


def test_file_missing_columns_is_rejected(upload):
    response = upload("readings.csv", "date,city,PM2.5\n2024-11-20,Haifa,10")

    assert response.status_code == 400
    assert "Missing columns: ['no2', 'co2']" in response.json()["detail"]


def test_empty_file_is_skipped(upload):
    response = upload("readings.csv", "")

    assert response.status_code == 200
    assert response.json()["reason"] == "file is empty"


def test_database_unavailable_returns_503(upload_rows):
    with patch("air_quality_db.queries.get_connection", side_effect=psycopg.OperationalError("connection refused")):
        response = upload_rows(HAIFA_20)

    assert response.status_code == 503


# Sample datasets


@pytest.mark.parametrize("path", SAMPLE_FILES, ids=lambda path: path.name)
def test_each_sample_file_saves_its_valid_rows(upload, path):
    data = upload(path.name, path.read_bytes()).json()
    rows_in_file = len(path.read_text().splitlines()) - 1
    skipped = SAMPLE_SKIPPED_LINES[path.name]

    assert data["skipped_rows"] == skipped
    assert data["inserted_rows"] == rows_in_file - len(skipped)


def test_all_samples_together(load_samples):
    assert all(response.status_code == 200 for response in load_samples.values())
    assert count_rows(READINGS_TABLE) == SAMPLE_TOTAL_READINGS
    assert count_rows(ALERTS_TABLE) == SAMPLE_TOTAL_READINGS


def test_uploading_the_samples_twice_adds_nothing(load_samples, upload):
    second_round = [upload(path.name, path.read_bytes()).json() for path in SAMPLE_FILES]

    assert sum(data["inserted_rows"] for data in second_round) == 0
    assert count_rows(READINGS_TABLE) == SAMPLE_TOTAL_READINGS
