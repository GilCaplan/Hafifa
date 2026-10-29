"""GET /alerts, GET /alerts/date and GET /alerts/city"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from air_quality_api.const import AqiConsts
from air_quality_db.models import Reading
from tests.const import SAMPLE_FILES
from tests.utils import SAMPLE_READINGS, client, upload

DATABASE_DOWN = OperationalError("connect", {}, Exception("connection refused"))
EXPECTED_ALERTS = [reading for reading in SAMPLE_READINGS if reading[Reading.aqi.key] > AqiConsts.ALERT_THRESHOLD]


# GET /alerts


@pytest.mark.usefixtures("load_samples")
def test_uploading_twice_does_not_duplicate_alerts() -> None:
    for path in SAMPLE_FILES:
        upload(path.name, path.read_bytes())

    assert len(client.get("/alerts").json()) == len(EXPECTED_ALERTS)


# GET /alerts/date


@pytest.mark.usefixtures("load_samples")
def test_alerts_by_date_outside_the_data_is_rejected() -> None:
    last = max(reading[Reading.date.key] for reading in SAMPLE_READINGS)
    day_after = str(date.fromisoformat(last) + timedelta(days=1))

    assert client.get("/alerts/date", params={"date": day_after}).status_code == 404


def test_alerts_by_invalid_date_is_rejected() -> None:
    assert client.get("/alerts/date", params={"date": "banana"}).status_code == 422


# GET /alerts/city


def test_alerts_by_city_database_unavailable_returns_503() -> None:
    city = SAMPLE_READINGS[0][Reading.city.key]
    with patch("air_quality_db.queries.get_session", side_effect=DATABASE_DOWN):
        response = client.get("/alerts/city", params={"city": city})

    assert response.status_code == 503
