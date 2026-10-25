"""GET /air-quality (date range) and GET /air-quality/city"""

import pytest

from tests.data import (
    ARAD_20,
    EILAT_20,
    HAIFA_20,
    HAIFA_21,
    SAMPLE_FIRST_DATE,
    SAMPLE_LAST_DATE,
    SAMPLE_READINGS_PER_CITY,
    SAMPLE_READINGS_PER_DATE,
    SAMPLE_TOTAL_READINGS,
)

HAIFA_19 = ("2024-11-19", "Haifa", 10, 20, 4)


def get_range(client, start_date, end_date):
    return client.get("/air-quality", params={"start_date": start_date, "end_date": end_date})


# GET /air-quality: basic


def test_range_returns_only_its_readings_sorted_by_date_then_city(client, upload_rows):
    upload_rows(HAIFA_19, HAIFA_20, EILAT_20, ARAD_20, HAIFA_21)
    response = get_range(client, "2024-11-20", "2024-11-21")

    assert response.status_code == 200
    assert [(row["date"], row["city"]) for row in response.json()] == [
        ("2024-11-20", "Arad"),
        ("2024-11-20", "Eilat"),
        ("2024-11-20", "Haifa"),
        ("2024-11-21", "Haifa"),
    ]


def test_range_partly_outside_the_data_returns_what_exists(client, upload_rows):
    upload_rows(HAIFA_20, HAIFA_21)

    assert len(get_range(client, "2024-11-01", "2024-11-20").json()) == 1


def test_start_after_end_is_rejected(client, upload_rows):
    upload_rows(HAIFA_20)
    response = get_range(client, "2024-11-21", "2024-11-20")

    assert response.status_code == 400
    assert "after end_date" in response.json()["detail"]


def test_range_outside_the_data_is_rejected(client, upload_rows):
    upload_rows(HAIFA_20, HAIFA_21)
    response = get_range(client, "2024-12-01", "2024-12-31")

    assert response.status_code == 404
    assert "The data covers 2024-11-20 to 2024-11-21" in response.json()["detail"]


def test_empty_database_is_reported(client):
    response = get_range(client, "2024-11-20", "2024-11-21")

    assert response.status_code == 404
    assert "no data yet" in response.json()["detail"]


@pytest.mark.parametrize("bad_date", ["banana", "2024-02-30", "20-11-2024", ""])
def test_invalid_dates_are_rejected(client, bad_date):
    assert get_range(client, bad_date, "2024-11-21").status_code == 422


def test_missing_end_date_is_rejected(client):
    assert client.get("/air-quality", params={"start_date": "2024-11-20"}).status_code == 422


# GET /air-quality: sample datasets


def test_samples_two_day_range(client, load_samples):
    rows = get_range(client, "2024-11-21", "2024-11-22").json()

    assert len(rows) == SAMPLE_READINGS_PER_DATE["2024-11-21"] + SAMPLE_READINGS_PER_DATE["2024-11-22"]
    assert {row["date"] for row in rows} == {"2024-11-21", "2024-11-22"}


def test_samples_whole_month_returns_everything(client, load_samples):
    assert len(get_range(client, "2024-11-01", "2024-11-30").json()) == SAMPLE_TOTAL_READINGS


@pytest.mark.parametrize("day", SAMPLE_READINGS_PER_DATE)
def test_samples_single_day(client, load_samples, day):
    assert len(get_range(client, day, day).json()) == SAMPLE_READINGS_PER_DATE[day]


def test_samples_day_before_the_data_is_rejected(client, load_samples):
    response = get_range(client, "2024-11-18", "2024-11-18")

    assert response.status_code == 404
    assert f"The data covers {SAMPLE_FIRST_DATE} to {SAMPLE_LAST_DATE}" in response.json()["detail"]


# GET /air-quality/city: basic


def test_city_returns_only_that_city(client, upload_rows):
    upload_rows(HAIFA_20, HAIFA_21, EILAT_20)
    rows = client.get("/air-quality/city", params={"city": "Haifa"}).json()

    assert len(rows) == 2
    assert {row["city"] for row in rows} == {"Haifa"}
    assert set(rows[0]) == {"id", "date", "city", "pm25", "no2", "co2", "aqi", "aqi_level"}


def test_city_name_spaces_are_trimmed(client, upload_rows):
    upload_rows(HAIFA_20)

    assert len(client.get("/air-quality/city", params={"city": "   Haifa  "}).json()) == 1


def test_unknown_city_is_rejected(client, upload_rows):
    upload_rows(HAIFA_20)

    assert client.get("/air-quality/city", params={"city": "Atlantis"}).status_code == 404


@pytest.mark.parametrize("bad_city", ["", "   ", "City123", "Haifa'; DROP TABLE alerts;--", "a" * 101])
def test_malformed_city_is_rejected(client, upload_rows, bad_city):
    upload_rows(HAIFA_20)

    assert client.get("/air-quality/city", params={"city": bad_city}).status_code == 400


# GET /air-quality/city: sample datasets


@pytest.mark.parametrize("city", SAMPLE_READINGS_PER_CITY)
def test_samples_each_city(client, load_samples, city):
    rows = client.get("/air-quality/city", params={"city": city}).json()

    assert len(rows) == SAMPLE_READINGS_PER_CITY[city]
    assert {row["city"] for row in rows} == {city}
