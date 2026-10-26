"""GET /aqi/history, GET /aqi/average and GET /aqi/best-cities"""

import pytest

from air_quality_api.const import Aqi, Columns
from tests.utils import SAMPLE_READINGS, client


def average_aqi_per_city() -> dict[str, float]:
    by_city: dict[str, list[float]] = {}
    for reading in SAMPLE_READINGS:
        by_city.setdefault(reading[Columns.CITY], []).append(reading[Columns.AQI])
    return {city: round(sum(values) / len(values), Aqi.AVERAGE_DECIMALS) for city, values in by_city.items()}


EXPECTED_AVERAGES = average_aqi_per_city()


# GET /aqi/history


@pytest.mark.usefixtures("load_samples")
def test_history_is_each_citys_aqi_sorted_by_date() -> None:
    for city in {reading[Columns.CITY] for reading in SAMPLE_READINGS}:
        expected = sorted(
            (r[Columns.DATE], r[Columns.AQI], r[Columns.AQI_LEVEL]) for r in SAMPLE_READINGS if r[Columns.CITY] == city
        )
        rows = client.get("/aqi/history", params={"city": city}).json()

        assert set(rows[0]) == {"date", "city", "aqi", "aqi_level"}
        assert [(row[Columns.DATE], row[Columns.AQI_LEVEL]) for row in rows] == [
            (day, level) for day, _, level in expected
        ], city
        assert [row[Columns.AQI] for row in rows] == pytest.approx([aqi for _, aqi, _ in expected]), city


# GET /aqi/average


@pytest.mark.usefixtures("load_samples")
def test_average_of_each_city() -> None:
    for city, average in EXPECTED_AVERAGES.items():
        response = client.get("/aqi/average", params={"city": city})

        assert response.json() == {Columns.CITY: city, Aqi.AVERAGE_KEY: average}


@pytest.mark.usefixtures("load_samples")
def test_average_trims_the_city_name() -> None:
    city = SAMPLE_READINGS[0][Columns.CITY]

    assert client.get("/aqi/average", params={"city": f"   {city} "}).json()[Columns.CITY] == city


# GET /aqi/best-cities


@pytest.mark.usefixtures("load_samples")
def test_best_cities_are_the_lowest_averages_with_ties_broken_by_name() -> None:
    ranked = sorted(EXPECTED_AVERAGES.items(), key=lambda item: (item[1], item[0]))
    best = client.get("/aqi/best-cities").json()

    assert [(row[Columns.CITY], row[Aqi.AVERAGE_KEY]) for row in best] == ranked[: Aqi.BEST_CITIES_COUNT]


def test_best_cities_with_no_data() -> None:
    assert client.get("/aqi/best-cities").json() == []
