"""GET /alerts, GET /alerts/date and GET /alerts/city"""

from unittest.mock import patch

import psycopg
import pytest

from air_quality_api.const import ALERT_AQI_THRESHOLD
from tests.data import (
    ARAD_20,
    EILAT_20,
    HAIFA_20,
    SAMPLE_FIRST_DATE,
    SAMPLE_LAST_DATE,
    SAMPLE_READINGS_PER_CITY,
    SAMPLE_READINGS_PER_DATE,
    SAMPLE_TOTAL_READINGS,
    aqi_of,
)

EILAT_21 = ("2024-11-21", "Eilat", 350, 20, 4)


# GET /alerts: basic


def test_only_readings_over_the_threshold_become_alerts(client, upload_rows):
    upload_rows(HAIFA_20, ARAD_20, EILAT_20)
    alerts = client.get("/alerts").json()

    assert len(alerts) == 1
    assert {key: alerts[0][key] for key in ("date", "city")} == {"date": "2024-11-20", "city": "Eilat"}
    assert alerts[0]["aqi"] == pytest.approx(aqi_of(EILAT_20))
    assert alerts[0]["aqi"] > ALERT_AQI_THRESHOLD


def test_no_alerts(client, upload_rows):
    upload_rows(HAIFA_20)

    assert client.get("/alerts").json() == []


def test_alert_threshold_is_strictly_over_300(client, upload_rows):
    # PM2.5 250.4 is the top of calculate_aqi's 201-300 band, so it scores exactly 300; 250.5 starts the next band
    exactly_300 = ("2024-11-20", "Haifa", 250.4, 20, 4)
    just_over = ("2024-11-20", "Eilat", 250.5, 20, 4)
    assert aqi_of(exactly_300) == ALERT_AQI_THRESHOLD
    upload_rows(exactly_300, just_over)

    assert [alert["city"] for alert in client.get("/alerts").json()] == ["Eilat"]


def test_uploading_twice_does_not_duplicate_alerts(client, upload_rows):
    upload_rows(EILAT_20)
    upload_rows(EILAT_20)

    assert len(client.get("/alerts").json()) == 1


# GET /alerts: sample datasets


def test_samples_every_reading_is_an_alert(client, load_samples):
    assert len(client.get("/alerts").json()) == SAMPLE_TOTAL_READINGS


# GET /alerts/date: basic


def test_alerts_by_date_returns_only_that_day(client, upload_rows):
    upload_rows(EILAT_20, EILAT_21, HAIFA_20)
    alerts = client.get("/alerts/date", params={"date": "2024-11-21"}).json()

    assert [(alert["date"], alert["city"]) for alert in alerts] == [("2024-11-21", "Eilat")]


def test_alerts_by_date_with_data_but_no_alerts(client, upload_rows):
    upload_rows(HAIFA_20)

    response = client.get("/alerts/date", params={"date": "2024-11-20"})
    assert response.status_code == 200
    assert response.json() == []


def test_alerts_by_date_outside_the_data_is_rejected(client, upload_rows):
    upload_rows(EILAT_20)

    assert client.get("/alerts/date", params={"date": "2099-01-01"}).status_code == 404


@pytest.mark.parametrize("bad_date", ["banana", "2024-02-30", ""])
def test_alerts_by_invalid_date_is_rejected(client, bad_date):
    assert client.get("/alerts/date", params={"date": bad_date}).status_code == 422


# GET /alerts/date: sample datasets


@pytest.mark.parametrize("day", SAMPLE_READINGS_PER_DATE)
def test_samples_alerts_per_day(client, load_samples, day):
    alerts = client.get("/alerts/date", params={"date": day}).json()

    assert len(alerts) == SAMPLE_READINGS_PER_DATE[day]
    assert {alert["date"] for alert in alerts} == {day}


def test_samples_alerts_day_after_the_data_is_rejected(client, load_samples):
    response = client.get("/alerts/date", params={"date": "2024-11-26"})

    assert response.status_code == 404
    assert f"The data covers {SAMPLE_FIRST_DATE} to {SAMPLE_LAST_DATE}" in response.json()["detail"]


# GET /alerts/city: basic


def test_alerts_by_city_sorted_by_date(client, upload_rows):
    upload_rows(EILAT_21, EILAT_20, HAIFA_20)
    alerts = client.get("/alerts/city", params={"city": "Eilat"}).json()

    assert [alert["date"] for alert in alerts] == ["2024-11-20", "2024-11-21"]


def test_alerts_by_city_with_readings_but_no_alerts(client, upload_rows):
    upload_rows(HAIFA_20)

    response = client.get("/alerts/city", params={"city": "Haifa"})
    assert response.status_code == 200
    assert response.json() == []


def test_alerts_by_unknown_city_is_rejected(client, upload_rows):
    upload_rows(EILAT_20)

    assert client.get("/alerts/city", params={"city": "Atlantis"}).status_code == 404


def test_alerts_by_malformed_city_is_rejected(client):
    assert client.get("/alerts/city", params={"city": "Eilat123"}).status_code == 400


def test_alerts_by_city_database_unavailable_returns_503(client):
    with patch("air_quality_db.queries.get_connection", side_effect=psycopg.OperationalError("connection refused")):
        response = client.get("/alerts/city", params={"city": "Eilat"})

    assert response.status_code == 503


# GET /alerts/city: sample datasets


@pytest.mark.parametrize("city", SAMPLE_READINGS_PER_CITY)
def test_samples_alerts_per_city(client, load_samples, city):
    alerts = client.get("/alerts/city", params={"city": city}).json()

    assert len(alerts) == SAMPLE_READINGS_PER_CITY[city]
    assert [alert["date"] for alert in alerts] == sorted(alert["date"] for alert in alerts)
