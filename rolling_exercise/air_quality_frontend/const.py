"""Constants for the frontend: where its web files are, and its logs and table-browsing endpoints."""

from pathlib import Path

from air_quality_api.const import ALERTS_TABLE, READINGS_TABLE

# The web page (HTML, CSS, JS), served at FRONTEND_ROUTE. Only this folder is public, not the Python files next to it.
STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_ROUTE = "/"

# GET /logs: reads the log file back for the logs panel.
# Matches the first line of an entry written with LOG_FORMAT (air_quality_api/const.py), so it must follow that format.
# Lines that don't match (like tracebacks) continue the previous entry.
# The request id part is optional so lines written before it was added still parse.
LOG_LINE_PATTERN = (
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<logger>\S+) - (?P<level>[A-Z]+) - "
    r"(?:\[(?P<request_id>[^\]]*)\] - )?(?P<message>.*)$"
)
DEFAULT_LOG_LIMIT = 300
MAX_LOG_LIMIT = 2000

# GET /tables/{table}: URL name -> database table and the columns that can be shown and sorted
BROWSABLE_TABLES = {
    "readings": {"table": READINGS_TABLE, "columns": ["id", "date", "city", "pm25", "no2", "co2", "aqi", "aqi_level"]},
    "alerts": {"table": ALERTS_TABLE, "columns": ["id", "date", "city", "aqi"]},
}
DEFAULT_SORT_COLUMN = "date"
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200
