from datetime import date

from fastapi import HTTPException, status

from air_quality_api.const import Tables, Validation
from air_quality_db.queries import count_rows, get_date_range


def clean_city_name(city: str) -> str:
    cleaned = " ".join(city.split())
    if not cleaned:
        raise ValueError("City name is empty")
    if len(cleaned) > Validation.MAX_CITY_NAME_LENGTH:
        raise ValueError(f"City name is longer than {Validation.MAX_CITY_NAME_LENGTH} characters")
    if not Validation.CITY_NAME_REGEX.match(cleaned):
        raise ValueError(f"City name {cleaned!r} can only contain letters, spaces, hyphens and apostrophes")
    return cleaned


def validate_city(city: str) -> str:
    try:
        cleaned = clean_city_name(city)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    if count_rows(Tables.READINGS, city=cleaned) == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No readings for city {cleaned}. Check the spelling: city names are case-sensitive",
        )
    return cleaned


def validate_dates(start_date: date, end_date: date) -> None:
    """Raises 400 if start_date is after end_date, 404 if the data doesn't overlap the range."""
    if start_date > end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"start_date {start_date} is after end_date {end_date}")

    first, last = get_date_range(Tables.READINGS)
    if first is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There is no data yet, upload a CSV first")
    if end_date < first or start_date > last:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No data for these dates. The data covers {first} to {last}")
