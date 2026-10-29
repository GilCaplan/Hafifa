"""POST /air-quality/upload"""

from pathlib import Path

from air_quality_api.const import AqiConsts
from air_quality_db.models import Alert, Reading
from air_quality_db.queries import count_rows
from tests.const import FILE_KEY, SAMPLE_FILES, SampleReading
from tests.utils import SAMPLE_READINGS, SAMPLE_SKIPPED_LINES, upload

FIRST_SAMPLE = SAMPLE_FILES[0]


def readings_of(path: Path) -> list[SampleReading]:
    return [reading for reading in SAMPLE_READINGS if reading[FILE_KEY] == path.name]


def count_alerts(readings: list[SampleReading]) -> int:
    return sum(reading[Reading.aqi.key] > AqiConsts.ALERT_THRESHOLD for reading in readings)


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
            "reason": None,
        }
    assert count_rows(Reading) == len(SAMPLE_READINGS)
    assert count_rows(Alert) == count_alerts(SAMPLE_READINGS)


def test_uploading_a_file_again_skips_its_rows_as_duplicates() -> None:
    upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes())
    data = upload(FIRST_SAMPLE.name, FIRST_SAMPLE.read_bytes()).json()

    assert (data["inserted_rows"], data["alerts"]) == (0, 0)
    assert data["duplicate_rows"] == len(readings_of(FIRST_SAMPLE))


def test_non_csv_file_is_rejected() -> None:
    response = upload(f"{FIRST_SAMPLE.stem}.txt", FIRST_SAMPLE.read_bytes())

    assert response.status_code == 400
    assert "not a CSV file" in response.json()["detail"]


def test_file_missing_columns_is_rejected() -> None:
    content = "\n".join(",".join(line.split(",")[:3]) for line in FIRST_SAMPLE.read_text().splitlines())
    response = upload(FIRST_SAMPLE.name, content)

    assert response.status_code == 400
    assert "Missing columns: ['no2', 'co2']" in response.json()["detail"]


def test_file_with_the_same_column_twice_is_rejected() -> None:
    header, *rows = FIRST_SAMPLE.read_text().splitlines()
    # A "pm25" column next to the file's "PM2.5": both clean to "pm25"
    content = "\n".join([f"{header},pm25", *(f"{row},{row.split(',')[2]}" for row in rows)])
    response = upload(FIRST_SAMPLE.name, content)

    assert response.status_code == 400
    assert "the same column more than once: ['pm25']" in response.json()["detail"]


def test_empty_file_is_skipped() -> None:
    response = upload("empty.csv", "")

    assert response.status_code == 200
    assert response.json()["reason"] == "file is empty"
