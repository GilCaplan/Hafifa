"""GET /alerts, GET /alerts/date and GET /alerts/city"""

from datetime import date, timedelta
from unittest.mock import patch

import psycopg
import pytest

from air_quality_api.const import Aqi, Columns
from tests.const import SAMPLE_FILES
from tests.utils import SAMPLE_READINGS, client, upload

EXPECTED_ALERTS = [reading for reading in SAMPLE_READINGS if reading[Columns.AQI] > Aqi.ALERT_THRESHOLD]


# GET /alerts


@pytest.mark.usefixtures("load_samples")
def test_uploading_twice_does_not_duplicate_alerts() -> None:
    for path in SAMPLE_FILES:
        upload(path.name, path.read_bytes())

    assert len(client.get("/alerts").json()) == len(EXPECTED_ALERTS)


# GET /alerts/date


@pytest.mark.usefixtures("load_samples")
def test_alerts_by_date_outside_the_data_is_rejected() -> None:
    last = max(reading[Columns.DATE] for reading in SAMPLE_READINGS)
    day_after = str(date.fromisoformat(last) + timedelta(days=1))

    assert client.get("/alerts/date", params={"date": day_after}).status_code == 404


def test_alerts_by_invalid_date_is_rejected() -> None:
    assert client.get("/alerts/date", params={"date": "banana"}).status_code == 422


# GET /alerts/city


def test_alerts_by_city_database_unavailable_returns_503() -> None:
    city = SAMPLE_READINGS[0][Columns.CITY]
    with patch("air_quality_db.queries.get_connection", side_effect=psycopg.OperationalError("connection refused")):
        response = client.get("/alerts/city", params={"city": city})

    assert response.status_code == 503
