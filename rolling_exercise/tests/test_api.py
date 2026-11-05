"""
Acceptance tests: one table per route. Each case is (what it tests, input, expected status, expected response body).
Every test starts with empty tables; the cases marked with the `uploaded` fixture first upload CSV below.
"""

from unittest.mock import ANY, patch

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.exc import OperationalError

from app.main import app
from app.support.config import settings

client = TestClient(app)

# AQI is driven by NO2 alone (PM2.5 and CO2 are 0): 53 -> 50, 100 -> 100, 360 -> 150, 2049 -> 500 (an alert).
# Lines 8 and 9 are invalid: a missing NO2 and a PM2.5 that isn't a number.
CSV_NAME = "readings.csv"
CSV = """date,city,PM2.5,NO2,CO2
2024-11-19,Haifa,0,53,0
2024-11-19,Tel Aviv,0,100,0
2024-11-19,Eilat,0,2049,0
2024-11-20,Haifa,0,100,0
2024-11-20,Tel Aviv,0,360,0
2024-11-20,Akko,0,53,0
2024-11-20,Ashdod,0,,0
2024-11-20,Ashdod,abc,53,0
"""


def reading(reading_id: int, day: str, city: str, no2: float, aqi: float, aqi_level: str) -> dict:
    return {
        "id": reading_id,
        "date": day,
        "city": city,
        "pm25": 0.0,
        "no2": no2,
        "co2": 0.0,
        "aqi": aqi,
        "aqi_level": aqi_level,
    }


def history(row: dict) -> dict:
    return {key: row[key] for key in ("date", "city", "aqi", "aqi_level")}


HAIFA_19 = reading(1, "2024-11-19", "Haifa", 53, 50, "Good")
TEL_AVIV_19 = reading(2, "2024-11-19", "Tel Aviv", 100, 100, "Moderate")
EILAT_19 = reading(3, "2024-11-19", "Eilat", 2049, 500, "Hazardous")
HAIFA_20 = reading(4, "2024-11-20", "Haifa", 100, 100, "Moderate")
TEL_AVIV_20 = reading(5, "2024-11-20", "Tel Aviv", 360, 150, "Unhealthy for Sensitive Groups")
AKKO_20 = reading(6, "2024-11-20", "Akko", 53, 50, "Good")
EILAT_ALERT = {"id": 1, "date": "2024-11-19", "city": "Eilat", "aqi": 500.0}

CITY_ROUTES = ["/air-quality/city", "/aqi/history", "/aqi/average", "/alerts/city"]
LETTERS_ONLY = "can only contain letters, spaces, hyphens and apostrophes"
BAD_CITIES = [
    pytest.param(
        "Atlantis",
        404,
        "No readings for city Atlantis. Check the spelling: city names are case-sensitive",
        id="unknown city",
    ),
    pytest.param("   ", 400, "City name is empty", id="empty city"),
    pytest.param("City123", 400, f"City name 'City123' {LETTERS_ONLY}", id="city with digits"),
    pytest.param(
        "Haifa'; DROP TABLE alerts;--",
        400,
        f'City name "Haifa\'; DROP TABLE alerts;--" {LETTERS_ONLY}',
        id="SQL in the city",
    ),
    pytest.param("a" * 101, 400, "City name is longer than 100 characters", id="city too long"),
]


def upload(content: str | bytes, filename: str = CSV_NAME) -> Response:
    return client.post("/air-quality/upload", files={"file": (filename, content, "text/csv")})


def upload_summary(filename: str = CSV_NAME, **counts: int | list[int] | str) -> dict:
    summary = {"filename": filename, "inserted_rows": 0, "duplicate_rows": 0, "skipped_rows": [], "alerts": 0}
    return summary | {"reason": None} | counts


@pytest.fixture
def uploaded() -> None:
    assert upload(CSV).status_code == 200


# POST /air-quality/upload


@pytest.mark.parametrize(
    ("filename", "content", "expected_status", "expected_body"),
    [
        pytest.param(
            CSV_NAME,
            CSV,
            200,
            upload_summary(inserted_rows=6, skipped_rows=[8, 9], alerts=1),
            id="saves the valid rows, skips invalid lines, counts alerts",
        ),
        pytest.param(
            "empty.csv",
            "",
            200,
            upload_summary("empty.csv", reason="file is empty"),
            id="empty file saves nothing",
        ),
        pytest.param(
            "image.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            400,
            {
                "detail": "Could not parse image.png as CSV "
                "('utf-8' codec can't decode byte 0x89 in position 0: invalid start byte)"
            },
            id="not a CSV",
        ),
        pytest.param(
            CSV_NAME,
            "date,city,PM2.5\n2024-11-19,Haifa,0\n",
            400,
            {
                "detail": "readings.csv has columns ['date', 'city', 'pm25'], "
                "expected ['date', 'city', 'pm25', 'no2', 'co2']"
            },
            id="missing columns",
        ),
        pytest.param(
            CSV_NAME,
            "date,city,PM2.5,NO2,CO2,pm25\n2024-11-19,Haifa,0,53,0,0\n",
            400,
            {
                "detail": "readings.csv has columns ['date', 'city', 'pm25', 'no2', 'co2', 'pm25'], "
                "expected ['date', 'city', 'pm25', 'no2', 'co2']"
            },
            id="same column twice (PM2.5 and pm25)",
        ),
    ],
)
def test_upload(filename: str, content: str | bytes, expected_status: int, expected_body: dict) -> None:
    response = upload(content, filename)

    assert response.status_code == expected_status
    assert response.json() == expected_body


@pytest.mark.usefixtures("uploaded")
def test_upload_same_file_again_skips_duplicates() -> None:
    response = upload(CSV)

    assert response.status_code == 200
    assert response.json() == upload_summary(duplicate_rows=6, skipped_rows=[8, 9])


# GET routes, with CSV uploaded


@pytest.mark.usefixtures("uploaded")
@pytest.mark.parametrize(
    ("path", "params", "expected_status", "expected_body"),
    [
        # GET /air-quality
        pytest.param(
            "/air-quality",
            {"start_date": "2024-11-19", "end_date": "2024-11-19"},
            200,
            [EILAT_19, HAIFA_19, TEL_AVIV_19],
            id="air-quality: one day, sorted by city",
        ),
        pytest.param(
            "/air-quality",
            {"start_date": "2024-11-19", "end_date": "2024-11-20"},
            200,
            [EILAT_19, HAIFA_19, TEL_AVIV_19, AKKO_20, HAIFA_20, TEL_AVIV_20],
            id="air-quality: whole range, sorted by date then city",
        ),
        pytest.param(
            "/air-quality",
            {"start_date": "2024-11-20", "end_date": "2024-11-19"},
            400,
            {"detail": "start_date 2024-11-20 is after end_date 2024-11-19"},
            id="air-quality: start after end",
        ),
        pytest.param(
            "/air-quality",
            {"start_date": "2024-11-21", "end_date": "2024-11-30"},
            404,
            {"detail": "No data for these dates. The data covers 2024-11-19 to 2024-11-20"},
            id="air-quality: range outside the data",
        ),
        pytest.param(
            "/air-quality",
            {"start_date": "banana", "end_date": "2024-11-20"},
            422,
            ANY,
            id="air-quality: invalid date",
        ),
        pytest.param(
            "/air-quality",
            {"start_date": "2024-11-19"},
            422,
            ANY,
            id="air-quality: missing end_date",
        ),
        # GET /air-quality/city
        pytest.param(
            "/air-quality/city",
            {"city": "Haifa"},
            200,
            [HAIFA_19, HAIFA_20],
            id="air-quality/city: the city's readings by date",
        ),
        pytest.param(
            "/air-quality/city",
            {"city": "  Tel   Aviv "},
            200,
            [TEL_AVIV_19, TEL_AVIV_20],
            id="air-quality/city: extra spaces are ignored",
        ),
        # GET /aqi/history
        pytest.param(
            "/aqi/history",
            {"city": "Haifa"},
            200,
            [history(HAIFA_19), history(HAIFA_20)],
            id="aqi/history: date, AQI and level by date",
        ),
        # GET /aqi/average
        pytest.param(
            "/aqi/average",
            {"city": "Tel Aviv"},
            200,
            {"city": "Tel Aviv", "average_aqi": 125.0},
            id="aqi/average: average of 100 and 150",
        ),
        # GET /aqi/best-cities
        pytest.param(
            "/aqi/best-cities",
            {},
            200,
            [
                {"city": "Akko", "average_aqi": 50.0},
                {"city": "Haifa", "average_aqi": 75.0},
                {"city": "Tel Aviv", "average_aqi": 125.0},
            ],
            id="aqi/best-cities: 3 lowest averages (Eilat, 500, left out)",
        ),
        # GET /alerts
        pytest.param("/alerts", {}, 200, [EILAT_ALERT], id="alerts: every alert"),
        # GET /alerts/date
        pytest.param("/alerts/date", {"date": "2024-11-19"}, 200, [EILAT_ALERT], id="alerts/date: day with an alert"),
        pytest.param("/alerts/date", {"date": "2024-11-20"}, 200, [], id="alerts/date: day without alerts"),
        pytest.param(
            "/alerts/date",
            {"date": "2024-11-21"},
            404,
            {"detail": "No data for these dates. The data covers 2024-11-19 to 2024-11-20"},
            id="alerts/date: day outside the data",
        ),
        pytest.param("/alerts/date", {"date": "banana"}, 422, ANY, id="alerts/date: invalid date"),
        # GET /alerts/city
        pytest.param("/alerts/city", {"city": "Eilat"}, 200, [EILAT_ALERT], id="alerts/city: city with an alert"),
        pytest.param("/alerts/city", {"city": "Haifa"}, 200, [], id="alerts/city: city without alerts"),
    ],
)
def test_get(path: str, params: dict, expected_status: int, expected_body: dict | list) -> None:
    response = client.get(path, params=params)

    assert response.status_code == expected_status
    assert response.json() == expected_body


# Every route that takes a city


@pytest.mark.usefixtures("uploaded")
@pytest.mark.parametrize("path", CITY_ROUTES)
@pytest.mark.parametrize(("city", "expected_status", "expected_detail"), BAD_CITIES)
def test_invalid_city(path: str, city: str, expected_status: int, expected_detail: str) -> None:
    response = client.get(path, params={"city": city})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


# Special states


def test_air_quality_with_no_data_yet() -> None:
    response = client.get("/air-quality", params={"start_date": "2024-11-19", "end_date": "2024-11-20"})

    assert response.status_code == 404
    assert response.json() == {"detail": "There is no data yet, upload a CSV first"}


def test_actions_are_logged_to_the_file() -> None:
    upload(CSV)
    client.get("/alerts/date", params={"date": "banana"})
    log = settings.log_file.read_text()

    assert "Skipped line 8 in readings.csv: missing or invalid no2" in log
    assert "Skipped line 9 in readings.csv: missing or invalid pm25" in log
    assert "Saved 6 rows and 1 alerts from readings.csv, 0 duplicates skipped" in log
    assert "POST /air-quality/upload -> 200" in log
    assert "Invalid request to /alerts/date: query.date:" in log


def test_database_unavailable() -> None:
    database_down = OperationalError("connect", {}, Exception("connection refused"))
    with patch("app.db.queries.get_session", side_effect=database_down):
        response = client.get("/alerts/city", params={"city": "Eilat"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable, try again later"}
