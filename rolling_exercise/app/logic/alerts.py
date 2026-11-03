import logging
from datetime import date

from app.db.models import Alert
from app.db.queries import fetch_rows
from app.logic.validation import validate_city, validate_dates
from app.schemas import AlertResponse

logger = logging.getLogger(__name__)


def get_all_alerts() -> list[AlertResponse]:
    alerts = [AlertResponse.model_validate(row) for row in fetch_rows(Alert)]

    logger.info(f"Found {len(alerts)} alerts")
    return alerts


def get_alerts_by_date(alert_date: date) -> list[AlertResponse]:
    validate_dates(alert_date, alert_date)
    rows = fetch_rows(Alert, start_date=alert_date, end_date=alert_date, sort=Alert.city)
    alerts = [AlertResponse.model_validate(row) for row in rows]

    logger.info(f"Found {len(alerts)} alerts on {alert_date}")
    return alerts


def get_alerts_by_city(city: str) -> list[AlertResponse]:
    city = validate_city(city)
    alerts = [AlertResponse.model_validate(row) for row in fetch_rows(Alert, city=city, sort=Alert.date)]

    logger.info(f"Found {len(alerts)} alerts for {city}")
    return alerts
