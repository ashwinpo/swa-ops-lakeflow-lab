# Context for AI assistants (Genie Code reads this file automatically)

This folder is a hands-on training lab. The person working here is learning Lakeflow Spark Declarative Pipelines, Genie Code, AI/BI dashboards, Genie, and Databricks Apps.

## Conventions

- Catalog: `temp_ai_training_2026`. Schema: the learner's username with non-letters replaced by `_` (e.g. `jane_doe`).
- Raw files: `/Volumes/temp_ai_training_2026/<schema>/raw/` — `bts/`, `weather_history/`, `reference/airports.csv`.
- The learner's pipeline lives in `my_pipeline/` (root folder). Tables are defined in `my_pipeline/transformations/`. `my_pipeline/utilities/metar_source.py` is a custom PySpark data source registered as `format("metar")`; read its docstring for options.
- `src/pipeline/` and `app/` are the instructor's reference solution. Don't copy from them unless the learner asks to compare.

## Data dictionary

**bts/*.csv** — US DOT BTS on-time performance, Southwest (WN) only, June–August 2026. One row per scheduled flight. Key columns: `FlightDate` (yyyy-MM-dd), `Origin`, `Dest`, `Flight_Number_Reporting_Airline`, `Tail_Number`, `CRSDepTime` (scheduled departure, local time, `hhmm` string like `0545`), `DepDelay` (minutes, negative = early), `DepDel15` (1.0 if ≥ 15 min late), `ArrDelay`, `ArrDel15`, `Cancelled` (1.0/0.0), `CancellationCode` (A carrier, B weather, C NAS, D security), `Diverted`, `TaxiOut`, `Distance`, `CarrierDelay`, `WeatherDelay`, `NASDelay`, `LateAircraftDelay`. Delay columns are empty for cancelled flights.

**weather_history/<AIRPORT>.csv** — hourly routine METAR reports from the Iowa Environmental Mesonet ASOS archive, same months. `station` (3-letter code, matches BTS `Origin`), `valid` (local time at the airport, `yyyy-MM-dd HH:mm`, usually at :51–:56), `tmpf` (°F), `dwpf`, `drct` (wind direction), `sknt` (wind, knots), `gust`, `vsby` (visibility, statute miles), `skyc1..3` (cloud cover: FEW/SCT/BKN/OVC/VV), `skyl1..3` (cloud base, feet), `wxcodes` (e.g. `TSRA` = thunderstorm with rain), `metar` (raw report). `M` = missing.

**reference/airports.csv** — 20 Southwest airports: `airport`, `icao` (K + code), `name`, `city`, `state`, `tz`, `latitude`, `longitude`.

**Live METAR stream** (`format("metar")`) — columns `station_id` (ICAO, e.g. `KDAL`), `observation_time` (UTC), `temp_c`, `wind_speed_kt`, `wind_gust_kt`, `visibility_mi`, `ceiling_ft`, `wx_string`, `flight_category` (VFR/MVFR/IFR/LIFR), `raw_text`, `source`, `ingest_time`.

## Definitions

- Flight category (FAA): LIFR ceiling < 500 ft or visibility < 1 mi; IFR < 1,000 ft or < 3 mi; MVFR ≤ 3,000 ft or ≤ 5 mi; else VFR. Ceiling = lowest BKN, OVC, or VV layer.
- A report at hh:53 describes conditions for departures in the following hour.
- "Delayed" = departure delay ≥ 15 minutes (DOT standard).

## How to help

When the learner asks you to build something, build it, and explain briefly what you did and why. Prefer streaming tables for raw incremental data and materialized views for joins and aggregations. Add table comments. When the learner says they're stuck or asks for a hint, use the `swa-lab-coach` skill if it's installed: hints first, not full answers.
