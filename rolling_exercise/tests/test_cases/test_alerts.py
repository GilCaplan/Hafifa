"""GET /alerts, GET /alerts/date and GET /alerts/city"""

from datetime import date, timedelta
from unittest.mock import patch

import psycopg
import pytest

from air_quality_api.const import (
    ALERT_AQI_THRESHOLD,
    AQI_COLUMN,
    CITY_COLUMN,
    DATE_COLUMN,
)
from tests.const import SAMPLE_FILES
from tests.utils import SAMPLE_READINGS, client, upload

EXPECTED_ALERTS = [reading for reading in SAMPLE_READINGS if reading[AQI_COLUMN] > ALERT_AQI_THRESHOLD]


# GET /alerts


@pytest.mark.usefixtures("load_samples")
def test_readings_over_the_threshold_become_alerts() -> None:
    expected = {(r[DATE_COLUMN], r[CITY_COLUMN]): r[AQI_COLUMN] for r in EXPECTED_ALERTS}
    alerts = {(alert[DATE_COLUMN], alert[CITY_COLUMN]): alert[AQI_COLUMN] for alert in client.get("/alerts").json()}

    assert alerts.keys() == expected.keys()
    for key, aqi in alerts.items():
        assert aqi == pytest.approx(expected[key]), key


@pytest.mark.usefixtures("load_samples")
def test_uploading_twice_does_not_duplicate_alerts() -> None:
    for path in SAMPLE_FILES:
        upload(path.name, path.read_bytes())

    assert len(client.get("/alerts").json()) == len(EXPECTED_ALERTS)


# GET /alerts/date


@pytest.mark.usefixtures("load_samples")
def test_alerts_by_date_returns_that_day_sorted_by_city() -> None:
    for day in {reading[DATE_COLUMN] for reading in SAMPLE_READINGS}:
        expected = sorted(r[CITY_COLUMN] for r in EXPECTED_ALERTS if r[DATE_COLUMN] == day)
        alerts = client.get("/alerts/date", params={"date": day}).json()

        assert [alert[CITY_COLUMN] for alert in alerts] == expected, day


@pytest.mark.usefixtures("load_samples")
def test_alerts_by_date_outside_the_data_is_rejected() -> None:
    last = max(reading[DATE_COLUMN] for reading in SAMPLE_READINGS)
    day_after = str(date.fromisoformat(last) + timedelta(days=1))

    assert client.get("/alerts/date", params={"date": day_after}).status_code == 404


def test_alerts_by_invalid_date_is_rejected() -> None:
    assert client.get("/alerts/date", params={"date": "banana"}).status_code == 422


# GET /alerts/city


@pytest.mark.usefixtures("load_samples")
def test_alerts_by_city_sorted_by_date() -> None:
    for city in {reading[CITY_COLUMN] for reading in SAMPLE_READINGS}:
        expected = sorted(r[DATE_COLUMN] for r in EXPECTED_ALERTS if r[CITY_COLUMN] == city)
        alerts = client.get("/alerts/city", params={"city": city}).json()

        assert [alert[DATE_COLUMN] for alert in alerts] == expected, city


def test_alerts_by_city_database_unavailable_returns_503() -> None:
    city = SAMPLE_READINGS[0][CITY_COLUMN]
    with patch("air_quality_db.queries.get_connection", side_effect=psycopg.OperationalError("connection refused")):
        response = client.get("/alerts/city", params={"city": city})

    assert response.status_code == 503
