"""GET /aqi/history, GET /aqi/average and GET /aqi/best-cities"""

import pytest

from air_quality_api.const import AqiConsts
from air_quality_db.models import Reading
from tests.utils import SAMPLE_READINGS, client


def average_aqi_per_city() -> dict[str, float]:
    by_city: dict[str, list[float]] = {}
    for reading in SAMPLE_READINGS:
        by_city.setdefault(reading[Reading.city.key], []).append(reading[Reading.aqi.key])
    return {city: round(sum(values) / len(values), AqiConsts.AVERAGE_DECIMALS) for city, values in by_city.items()}


EXPECTED_AVERAGES = average_aqi_per_city()


# GET /aqi/average


@pytest.mark.usefixtures("load_samples")
def test_average_of_each_city() -> None:
    for city, average in EXPECTED_AVERAGES.items():
        response = client.get("/aqi/average", params={"city": city})

        assert response.json() == {Reading.city.key: city, AqiConsts.AVERAGE_KEY: average}
