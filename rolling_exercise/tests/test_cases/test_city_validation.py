"""City validation, shared by every endpoint that takes a city (see validate_city)"""

import pytest

from tests.utils import client

CITY_ENDPOINTS = ["/air-quality/city", "/aqi/history", "/aqi/average", "/alerts/city"]


@pytest.mark.usefixtures("load_samples")
@pytest.mark.parametrize("path", CITY_ENDPOINTS)
def test_every_city_endpoint_rejects_unknown_and_malformed_cities(path: str) -> None:
    assert client.get(path, params={"city": "Atlantis"}).status_code == 404
    assert client.get(path, params={"city": "City123"}).status_code == 400


@pytest.mark.usefixtures("load_samples")
@pytest.mark.parametrize("bad_city", ["", "   ", "City123", "Haifa'; DROP TABLE alerts;--", "a" * 101])
def test_malformed_city_is_rejected(bad_city: str) -> None:
    assert client.get("/air-quality/city", params={"city": bad_city}).status_code == 400
