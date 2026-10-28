# Air Quality Index - Building an API

Yan and Sapir were sitting at a bakery in Haifa when they realized that the air surrounding them is very very polluted.
They decided that this is really dangerous and should be monitored. They thought about who could organize all this data and monitor it, and called their friends (and former co-workers) in Optimus team. And luckily, they have the best developers to do it! 

## Your Mission

This exercise is a rolling exercise that will include creating a DB and building an API with error handling, tests and loggers.
Examples for csv files are under the folder `air_quality_files/`

**The API will:**
- Process air quality data from various cities around the country.
- Calculate the AQI (Air Quality Index) for each city using a given function.
- Store the AQI data along with the pollutants (PM2.5, NO2, CO2) in a database for analysis and reporting.
- Allow residents to check the air quality by querying the system, so they can decide if it’s safe to walk in the park or if they should keep their windows shut.

## The API’s Functionality
You will need to implement the following functionalities:

- **Upload Air Quality Data:**
  residents at various cities will upload CSV files containing PM2.5, NO2, CO2 levels.
  Each file will also include a date and the city name.

- **Validate the Data:**
  Implement functionality to validate and clean uploaded data before saving it to the database.
  For example, Rows with missing or corrupted values should be logged and ignored.

- **Calculate the AQI:**
  You will use a function given to you in the file `calculate_aqi.py` to calculate the AQI based on
  the pollution levels.
  This AQI will be stored along with the pollutants.

- **Store Data in a Choosen Database:**
  The database will store the date, city name, PM2.5, NO2, CO2, and the calculated AQI.
  The data will be used for future analysis to track air quality trends across cities.
  If the AQI value is over 300, it will be saved in "alerts" table that will have the fields: date, city and AQI.
  Think about what database is the most compatible

- **Query for Insights:**
  You’ll create endpoints that allow residents to check the air quality in real-time.
  They will be able to query the system to see which city has the best or worst air quality on a given day.

- **Error Handling:**
  Not all data will be clean and valid, so your API should handle issues like missing pollutant data, invalid dates, or corrupt files gracefully.
  It should also return informative error messages to help users fix any problems with their uploads.

- **Logging:**
  The government wants to ensure that everything is logged for transparency and future auditing.
  All actions (like file uploads, data processing, AQI calculations) should be logged into a file.

- **Testing:**
  To ensure everything is ok and check all possible cases, you will need to create tests for every function you think is necessary. Use mock if needed.

### How the AQI Calculation Works
The AQI is a number that reflects how clean or polluted the air is, and it is calculated using the pollutant levels. Here's a simplified version of how it might work:

- PM2.5 is the most critical factor in the AQI calculation.
- NO2 and CO2 are secondary, but still important.

You will calculate it using a given function "calculate_aqi(pm25, no2, co2)" that will take the pollutant values and return an AQI value between 0 (good air quality) and 500 (hazardous air quality), and the AQI level (ranged from "Good" to "Hazardous"). The AQI data (AQI and AQI level) will be saved in the database for each row of data.

## API Endpoints

- **POST upload air quality data**
  - Description: Uploads air quality data from a CSV file to the database.
  - Request Body: A multipart/form-data request containing a CSV file.

- **GET air quality data**
  - Description: Retrieves air quality data for a specific date range.
  - Query Parameters:
    - start_date: The start date in YYYY-MM-DD format.
    - end_date: The end date in YYYY-MM-DD format.

- **GET air quality data by city**
  - Description: Retrieves air quality data for a specific city.
  - Query Parameters:
    - city: The name of the city.

- **GET city aqi history**
  - Description: Retrieves the AQI history for a specific city.
  - Query Parameters:
    - city: The name of the city.

- **GET city aqi average**
  - Description: Retrieves the AQI average for a specific city.
  - Query Parameters:
    - city: The name of the city.

- **GET best cities**
  - Description: Retrieves the 3 cities with the best air quality based on the AQI. The best
    cities will have the lowest AQI values.

- **GET all alerts**
  - Description: Retrieves all alerts.

- **GET all alerts by date**
  - Description: Retrieves all alerts from a specific date.
  - Query Parameters:
    - date: The date in YYYY-MM-DD format.

- **GET all alerts by city**
  - Description: Retrieves all alerts for a specific city.
  - Query Parameters:
    - city: The name of the city.


## Good Luck! (:

---

## Setup and running

### Requirements
- Python 3.13
- PostgreSQL 16 (e.g. `brew install postgresql@16 && brew services start postgresql@16` on macOS)

### 1. Install the Python packages
From this folder (`rolling_exercise/`):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r setup/requirements.txt
```

### 2. Create the database and its tables
```bash
createdb air_quality
psql air_quality -f air_quality_db/schema.sql
```
This creates two tables: `air_quality_readings` 
and `alerts` (readings with AQI over 300). Running `schema.sql` again is safe, since it skips tables that already exist.

### 3. Configure `setup/.env`
Create a `.env` file in the `setup/` folder:
```
HOST=127.0.0.1
PORT=8010
RELOAD=true

LOG_FILE=air_quality_files/logs/air_quality.log
LOG_LEVEL=INFO

DATABASE_URL=postgresql://<your-postgres-user>@localhost:5432/air_quality
```
All six values are required: the server won't start if one is missing. A local Homebrew Postgres uses your macOS
username and no password.

### 4. Run the server
```bash
python main.py
```
- API docs: http://127.0.0.1:8010/docs
- Logs: written to `air_quality_files/logs/air_quality.log` (a relative `LOG_FILE` is relative to the project
  root, and its folder is created if missing).

Sample files to upload are in `air_quality_files/input/`.

### Running the tests
```bash
python -m tests            # all tests (uses setup/pytest.ini)
python -m tests -v         # one line per test
python -m tests -k alerts  # only tests whose name matches
```
The tests create their own database, `air_quality_test`, from `schema.sql`, and drop it when they finish, so your
`air_quality` database is never touched. They need the Postgres server running and your user allowed to create
databases (the default for a local Homebrew install). The tests upload the sample files in
`air_quality_files/input/` and compute the expected results from those files. Tests that simulate the database being
down use `unittest.mock`.

### Linting and formatting
Ruff, with its settings in `ruff.toml` in the project root. The VS Code Ruff extension finds it on its own; from the
command line (in the project root):
```bash
ruff check --fix .
ruff format .
```

### Project layout
| Path | Contents |
|---|---|
| `main.py` | Starts the server |
| `air_quality_api/api.py` | The API endpoints |
| `air_quality_api/handlers.py` | Middleware and error handlers: logs every call and turns errors, including database errors, into responses |
| `air_quality_api/upload.py` | The CSV upload pipeline: file validation, row cleaning, AQI calculation |
| `air_quality_api/utils.py` | City and date validation |
| `air_quality_api/logs.py` | Logging setup, the access log for API calls, and the upload's log messages |
| `air_quality_api/const.py` | Constants and settings read from `setup/.env` |
| `air_quality_db/` | Database connection (`connection.py`), queries (`queries.py`) and their helpers (`utils.py`), fixed SQL statements (`statements.py`) and `schema.sql` |
| `tests/` | Test database setup and sample uploads (`conftest.py`), the API client and expected sample data (`utils.py`), constants (`const.py`) |
| `tests/test_cases/` | The tests, one file per group of endpoints |
| `air_quality_files/input/` | Sample CSV files to upload |
| `air_quality_files/logs/` | The log file (`air_quality.log`), and the tests' log (`air_quality_test.log`, emptied on every run) |
| `setup/` | `.env`, `requirements.txt` and `pytest.ini` |
| `ruff.toml` | Ruff's lint and format settings |
| `calculate_aqi.py` | The given AQI function |

### Why PostgreSQL
- The data is a table: every reading has the same fixed fields (date, city, PM2.5, NO2, CO2, AQI, AQI level).
- The queries are mostly filtering and aggregation (date ranges, averages per city, best cities), which SQL does
  directly.
- Alerts are tied to readings. A foreign key guarantees every alert belongs to a stored reading, and
  `UNIQUE (date, city)` stops the same city and day from being stored twice.
- Constraints (`NOT NULL`, `CHECK (aqi > 300)` on alerts, non-negative pollutants) keep invalid data out even if
  something bypasses the API.
