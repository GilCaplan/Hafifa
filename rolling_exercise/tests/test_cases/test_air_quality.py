"""GET /air-quality (date range) and GET /air-quality/city"""

from collections import Counter
from datetime import date, timedelta

import pytest
from httpx import Response

from air_quality_db.models import Reading
from tests.utils import SAMPLE_READINGS, client

SAMPLE_DATES = sorted({reading[Reading.date.key] for reading in SAMPLE_READINGS})


def get_range(start_date: str, end_date: str) -> Response:
    return client.get("/air-quality", params={"start_date": start_date, "end_date": end_date})


def shift(day: str, days: int) -> str:
    return str(date.fromisoformat(day) + timedelta(days=days))


# GET /air-quality


@pytest.mark.usefixtures("load_samples")
def test_whole_range_returns_every_reading() -> None:
    assert len(get_range(SAMPLE_DATES[0], SAMPLE_DATES[-1]).json()) == len(SAMPLE_READINGS)


@pytest.mark.usefixtures("load_samples")
def test_single_days() -> None:
    for day, expected in Counter(reading[Reading.date.key] for reading in SAMPLE_READINGS).items():
        assert len(get_range(day, day).json()) == expected, day


@pytest.mark.usefixtures("load_samples")
def test_start_after_end_is_rejected() -> None:
    response = get_range(SAMPLE_DATES[1], SAMPLE_DATES[0])

    assert response.status_code == 400
    assert "after end_date" in response.json()["detail"]


@pytest.mark.usefixtures("load_samples")
def test_range_outside_the_data_is_rejected() -> None:
    day_after = shift(SAMPLE_DATES[-1], 1)
    response = get_range(day_after, day_after)

    assert response.status_code == 404
    assert f"The data covers {SAMPLE_DATES[0]} to {SAMPLE_DATES[-1]}" in response.json()["detail"]


def test_empty_database_is_reported() -> None:
    response = get_range(SAMPLE_DATES[0], SAMPLE_DATES[1])

    assert response.status_code == 404
    assert "no data yet" in response.json()["detail"]


@pytest.mark.parametrize("bad_date", ["banana", "2024-02-30", "20-11-2024", ""])
def test_invalid_dates_are_rejected(bad_date: str) -> None:
    assert get_range(bad_date, SAMPLE_DATES[0]).status_code == 422


def test_missing_end_date_is_rejected() -> None:
    assert client.get("/air-quality", params={"start_date": SAMPLE_DATES[0]}).status_code == 422


# GET /air-quality/city


@pytest.mark.usefixtures("load_samples")
def test_each_city_returns_only_its_readings() -> None:
    for city, expected in Counter(reading[Reading.city.key] for reading in SAMPLE_READINGS).items():
        rows = client.get("/air-quality/city", params={"city": city}).json()

        assert len(rows) == expected, city
        assert {row[Reading.city.key] for row in rows} == {city}
        assert set(rows[0]) == {"id", "date", "city", "pm25", "no2", "co2", "aqi", "aqi_level"}


@pytest.mark.usefixtures("load_samples")
def test_city_name_spaces_are_trimmed() -> None:
    city = SAMPLE_READINGS[0][Reading.city.key]
    expected = sum(reading[Reading.city.key] == city for reading in SAMPLE_READINGS)

    assert len(client.get("/air-quality/city", params={"city": f"   {city}  "}).json()) == expected
