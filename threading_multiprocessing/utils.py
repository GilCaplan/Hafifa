import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from const import *

logger = logging.getLogger(__name__)


def init_csv() -> None:
    """Create the CSV with only the header row, overwriting any previous run."""
    pd.DataFrame(columns=COLUMNS).to_csv(PATH, index=False)
    logger.info("Initialized %s", PATH)


def append_to_csv(rows: list[list]) -> pd.DataFrame:
    """Append rows of [hour, ticker, % change] to the CSV and return them as a DataFrame."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(PATH, mode="a", header=False, index=False)
    logger.info("Appended %d rows to %s", len(df), PATH)
    return df


def fetch_candle(ticker: str, hour: datetime) -> pd.DataFrame:
    """Return the 1-hour candle starting at hour, or an empty DataFrame if it can't be fetched."""
    for attempt in range(MAX_RETRIES):
        try:
            return yf.Ticker(ticker).history(
                start=hour, end=hour + timedelta(hours=1), interval="1h"
            )
        except YFRateLimitError:
            delay = RETRY_DELAY_SECONDS * 2**attempt
            logger.warning(
                "%s %s: rate limited, retry %d/%d in %ds",
                ticker,
                hour,
                attempt + 1,
                MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
        except Exception as e:  # noqa: BLE001
            logger.error("%s %s: fetch failed: %s", ticker, hour, e)
            break
    else:
        logger.error("%s %s: giving up after %d retries", ticker, hour, MAX_RETRIES)
    return pd.DataFrame()
