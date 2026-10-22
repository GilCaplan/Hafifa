import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from yfinance.exceptions import YFRateLimitError

load_dotenv()

BASE_DIR = Path(__file__).parent
PATH = BASE_DIR / os.environ["DESTINATION_FILE"]
COLUMNS = ["hour", "ticker", "percentage_change"]
TICKER_DATES_ENV = {
    "BTC-USD": "BITCOIN_DATES",
    "AMZN": "AMAZON_DATES",
    "GOOGL": "GOOGLE_DATES",
}
CRYPTO_TICKERS = {"BTC-USD"}
MARKET_OPEN_HOUR = 9  # the 9:00 hour contains the 9:30 open
MARKET_CLOSE_HOUR = 16
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def init_csv() -> None:
    """Create the CSV with only the header row, overwriting any previous run."""
    pd.DataFrame(columns=COLUMNS).to_csv(PATH, index=False)


def append_to_csv(rows: list[list]) -> pd.DataFrame:
    """Append rows of [hour, ticker, % change] to the CSV and return them as a DataFrame."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(PATH, mode="a", header=False, index=False)
    return df


def fetch_candle(ticker: str, hour: datetime) -> pd.DataFrame:
    """Return the 1-hour candle starting at hour, or an empty DataFrame if it can't be fetched."""
    for attempt in range(MAX_RETRIES):
        try:
            return yf.Ticker(ticker).history(
                start=hour, end=hour + timedelta(hours=1), interval="1h"
            )
        except YFRateLimitError:
            time.sleep(RETRY_DELAY_SECONDS * 2**attempt)
        except Exception as e:  # noqa: BLE001
            print(f"{ticker} {hour}: {e}")
            break
    return pd.DataFrame()


def is_trading_hour(ticker: str, hour: datetime) -> bool:
    """Crypto trades 24/7; stocks only on weekdays during market hours."""
    if ticker in CRYPTO_TICKERS:
        return True
    return hour.weekday() < 5 and MARKET_OPEN_HOUR <= hour.hour < MARKET_CLOSE_HOUR


def get_hourly_change(ticker: str, date_str: str) -> list:
    """Return [hour, ticker, % change] for the 1-hour candle containing date_str."""
    hour = datetime.fromisoformat(date_str).replace(minute=0, second=0, microsecond=0)
    if not is_trading_hour(ticker, hour):
        return [hour, ticker, None]
    candle = fetch_candle(ticker, hour)
    if candle.empty:
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
    rows = get_asset_changes(ticker, load_dates(dates_env))
    df = append_to_csv(rows)
    print(df.head(10))


if __name__ == "__main__":
    init_csv()
    for ticker, dates_env in TICKER_DATES_ENV.items():
        process_asset(ticker, dates_env)
