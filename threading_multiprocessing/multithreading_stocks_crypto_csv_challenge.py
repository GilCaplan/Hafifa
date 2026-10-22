import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from const import *
from utils import *

logger = logging.getLogger(__name__)


def is_trading_hour(ticker: str, hour: datetime) -> bool:
    """Crypto trades 24/7; stocks only on weekdays during market hours."""
    if ticker in CRYPTO_TICKERS:
        return True
    return (
        hour.weekday() < END_OF_WEEK
        and MARKET_OPEN_HOUR <= hour.hour < MARKET_CLOSE_HOUR
    )


def get_hourly_change(ticker: str, date_str: str) -> list:
    """Return [hour, ticker, % change] for the 1-hour candle containing date_str."""
    hour = datetime.fromisoformat(date_str).replace(minute=0, second=0, microsecond=0)
    if not is_trading_hour(ticker, hour):
        return [hour, ticker, None]
    candle = fetch_candle(ticker, hour)
    if candle.empty:
        logger.debug("%s %s: no candle data", ticker, hour)
        return [hour, ticker, None]
    open_price = candle["Open"].iloc[0]
    close_price = candle["Close"].iloc[0]
    return [hour, ticker, (close_price - open_price) / open_price * 100]


def load_dates(dates_env: str) -> list[str]:
    """Return the non-empty lines of the dates file named by the dates_env variable."""
    with open(BASE_DIR / os.environ[dates_env]) as f:
        return [line for line in f.read().splitlines() if line.strip()]


def get_asset_changes(ticker: str, dates: list[str]) -> list[list]:
    with ThreadPoolExecutor() as executor:
        return list(executor.map(partial(get_hourly_change, ticker), dates))


def process_asset(ticker: str, dates_env: str) -> None:
    """Fetch the hourly changes for one asset and append them to the shared CSV."""
    dates = load_dates(dates_env)
    logger.info("%s: fetching %d hours", ticker, len(dates))
    start = time.perf_counter()
    rows = get_asset_changes(ticker, dates)
    missing = sum(row[2] is None for row in rows)
    logger.info(
        "%s: done in %.1fs, %d rows (%d without data)",
        ticker,
        time.perf_counter() - start,
        len(rows),
        missing,
    )
    append_to_csv(rows)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
    )
    init_csv()
    for ticker, dates_env in TICKER_DATES_ENV.items():
        process_asset(ticker, dates_env)
