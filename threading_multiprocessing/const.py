import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

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
END_OF_WEEK = 5
