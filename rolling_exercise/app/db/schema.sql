CREATE TABLE IF NOT EXISTS air_quality_readings (
    id         SERIAL PRIMARY KEY,
    date       DATE NOT NULL,
    city       TEXT NOT NULL,
    pm25       DOUBLE PRECISION NOT NULL CHECK (pm25 >= 0),
    no2        DOUBLE PRECISION NOT NULL CHECK (no2 >= 0),
    co2        DOUBLE PRECISION NOT NULL CHECK (co2 >= 0),
    aqi        DOUBLE PRECISION NOT NULL CHECK (aqi BETWEEN 0 AND 500),
    aqi_level  TEXT NOT NULL,
    UNIQUE (date, city)
);

CREATE INDEX IF NOT EXISTS idx_air_quality_readings_city ON air_quality_readings (city);

CREATE TABLE IF NOT EXISTS alerts (
    id    SERIAL PRIMARY KEY,
    date  DATE NOT NULL,
    city  TEXT NOT NULL,
    aqi   DOUBLE PRECISION NOT NULL,
    UNIQUE (date, city),
    FOREIGN KEY (date, city) REFERENCES air_quality_readings (date, city) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_city ON alerts (city);
