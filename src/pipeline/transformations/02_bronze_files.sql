-- Raw files loaded by Lab 0, ingested incrementally with Auto Loader (read_files + STREAM).
-- ${lab.raw_path} is set in the pipeline configuration, e.g. /Volumes/temp_ai_training_2026/<you>/raw

CREATE OR REFRESH STREAMING TABLE bronze_bts_flights
COMMENT "Southwest (WN) flight-level on-time performance from BTS, as delivered."
AS SELECT *, _metadata.file_path AS source_file
FROM STREAM read_files(
  '${lab.raw_path}/bts',
  format => 'csv',
  header => true,
  schemaHints => 'CRSDepTime STRING, DepTime STRING, CRSArrTime STRING, ArrTime STRING, WheelsOff STRING, WheelsOn STRING'
);

CREATE OR REFRESH STREAMING TABLE bronze_weather_history
COMMENT "Hourly routine METARs per airport from the IEM ASOS archive. Timestamps are airport local time."
AS SELECT *, _metadata.file_path AS source_file
FROM STREAM read_files(
  '${lab.raw_path}/weather_history',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH MATERIALIZED VIEW dim_airports
COMMENT "Southwest airports used in the lab: code, ICAO ID, name, time zone, coordinates."
AS SELECT * FROM read_files('${lab.raw_path}/reference/airports.csv', format => 'csv', header => true);
