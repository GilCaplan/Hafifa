"""GET /aqi/history, GET /aqi/average and GET /aqi/best-cities"""

import pytest

from air_quality_api.const import AVERAGE_AQI_DECIMALS
from calculate_aqi import calculate_aqi
from tests.data import (
    ARAD_20,
    EILAT_20,
    HAIFA_20,
    HAIFA_21,
    SAMPLE_AQI,
    SAMPLE_READINGS_PER_CITY,
    TEL_AVIV_20,
    aqi_of,
)

HAIFA_19 = ("2024-11-19", "Haifa", 10, 20, 4)


# GET /aqi/history: basic


def test_history_is_sorted_by_date(client, upload_rows):
    upload_rows(HAIFA_21, HAIFA_19, HAIFA_20)  # uploaded out of order
    rows = client.get("/aqi/history", params={"city": "Haifa"}).json()

    assert [row["date"] for row in rows] == ["2024-11-19", "2024-11-20", "2024-11-21"]
    assert set(rows[0]) == {"date", "city", "aqi", "aqi_level"}
    assert rows[1]["aqi"] == pytest.approx(aqi_of(HAIFA_20))


def test_history_levels_match_calculate_aqi(client, upload_rows):
    upload_rows(HAIFA_20, HAIFA_21)
    levels = [row["aqi_level"] for row in client.get("/aqi/history", params={"city": "Haifa"}).json()]

    assert levels == [calculate_aqi(*HAIFA_20[2:])[1], calculate_aqi(*HAIFA_21[2:])[1]]


def test_history_unknown_city_is_rejected(client, upload_rows):
    upload_rows(HAIFA_20)

    assert client.get("/aqi/history", params={"city": "Atlantis"}).status_code == 404


def test_history_malformed_city_is_rejected(client):
    assert client.get("/aqi/history", params={"city": "Haifa!"}).status_code == 400


# GET /aqi/history: sample datasets


@pytest.mark.parametrize("city", SAMPLE_READINGS_PER_CITY)
def test_samples_history_has_every_day_in_order(client, load_samples, city):
    dates = [row["date"] for row in client.get("/aqi/history", params={"city": city}).json()]

    assert len(dates) == SAMPLE_READINGS_PER_CITY[city]
    assert dates == sorted(dates)


# GET /aqi/average: basic


def test_average_of_a_city(client, upload_rows):
    upload_rows(HAIFA_20, HAIFA_21, EILAT_20)
    expected = round((aqi_of(HAIFA_20) + aqi_of(HAIFA_21)) / 2, AVERAGE_AQI_DECIMALS)

    assert client.get("/aqi/average", params={"city": "Haifa"}).json() == {"city": "Haifa", "average_aqi": expected}


def test_average_trims_the_city_name(client, upload_rows):
    upload_rows(HAIFA_20)
    response = client.get("/aqi/average", params={"city": "   Haifa "}).json()

    assert response["city"] == "Haifa"
    assert response["average_aqi"] == round(aqi_of(HAIFA_20), AVERAGE_AQI_DECIMALS)


def test_average_unknown_city_is_rejected(client, upload_rows):
    upload_rows(HAIFA_20)

    assert client.get("/aqi/average", params={"city": "Atlantis"}).status_code == 404


def test_average_malformed_city_is_rejected(client):
    assert client.get("/aqi/average", params={"city": "City123"}).status_code == 400


# GET /aqi/average: sample datasets


@pytest.mark.parametrize("city", SAMPLE_READINGS_PER_CITY)
def test_samples_average(client, load_samples, city):
    assert client.get("/aqi/average", params={"city": city}).json()["average_aqi"] == SAMPLE_AQI


# GET /aqi/best-cities: basic


def test_best_cities_are_the_three_lowest_averages_in_order(client, upload_rows):
    upload_rows(ARAD_20, HAIFA_20, HAIFA_21, TEL_AVIV_20, EILAT_20)
    cities = [row["city"] for row in client.get("/aqi/best-cities").json()]

    assert cities == ["Arad", "Tel Aviv", "Haifa"]  # Eilat, the most polluted, is left out


def test_best_cities_ties_are_broken_by_name(client, upload_rows):
    same_air = (10, 20, 4)
    upload_rows(*[("2024-11-20", city, *same_air) for city in ["Netanya", "Arad", "Holon", "Eilat"]])

    assert [row["city"] for row in client.get("/aqi/best-cities").json()] == ["Arad", "Eilat", "Holon"]


def test_best_cities_with_fewer_than_three_cities(client, upload_rows):
    upload_rows(HAIFA_20, ARAD_20)

    assert [row["city"] for row in client.get("/aqi/best-cities").json()] == ["Arad", "Haifa"]


def test_best_cities_with_no_data(client):
    assert client.get("/aqi/best-cities").json() == []


# GET /aqi/best-cities: sample datasets


def test_samples_best_cities(client, load_samples):
    # Every sample city averages the same AQI, so the alphabetical tie-break decides
    best = client.get("/aqi/best-cities").json()

    assert [row["city"] for row in best] == sorted(SAMPLE_READINGS_PER_CITY)[:3]
    assert {row["average_aqi"] for row in best} == {SAMPLE_AQI}
