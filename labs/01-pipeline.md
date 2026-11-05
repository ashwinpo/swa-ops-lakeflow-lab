# Lab 1 — Build the pipeline

**Goal:** build the bronze and silver layers of a Lakeflow Spark Declarative Pipeline (SDP) in the Lakeflow Pipelines Editor. This includes a streaming table fed by a custom PySpark data source and two tables loaded with Auto Loader.

**You need:** `raw_path` from Lab 0, for example `/Volumes/temp_ai_training_2026/jane_doe/raw`.

## Key ideas

| Concept | What it means here |
|---|---|
| **Streaming table** | Append-only table that processes only new input each run. Used for raw data arriving over time: weather reports, new BTS files. |
| **Materialized view** | Table defined by a query. The pipeline keeps it up to date, incrementally when it can. Used for cleaned and aggregated data. |
| **Expectation** | A data quality rule on a table. Bad rows can be kept and counted, dropped, or made to fail the update. |
| **Custom data source** | A Python class that teaches Spark to read a new source with `spark.readStream.format("metar")`. Same idea as the OpenSky source in the original blog. |
| **Auto Loader** (`read_files` + `STREAM`) | Incrementally picks up new files in a volume. Each file is processed once. |

You declare *what* each table is. The pipeline works out the order, the dependencies, checkpoints, retries, and incremental processing.

---

## 1. Create the pipeline

1. In the left sidebar, click **Jobs & Pipelines** → **Create** → **ETL pipeline**.
2. Set:
   - **Name:** `<you>_ops_pipeline`
   - **Default catalog:** `temp_ai_training_2026`
   - **Default schema:** your schema from Lab 0
3. Choose **Start with an empty file**, language **Python**.

The editor opens with a pipeline root folder in your home directory containing a `transformations/` folder. Files in `transformations/` define tables. Other files in the root folder (like `utilities/`) can be imported but don't define tables.

## 2. Add the custom data source

1. In the editor's file browser, create a folder `utilities` in the pipeline root (next to `transformations`, not inside it).
2. In `utilities`, create a file `metar_source.py`.
3. Paste the contents of `src/pipeline/utilities/metar_source.py` from your lab folder.

Read the file before moving on. The parts that matter:

```python
class MetarDataSource(DataSource):
    @classmethod
    def name(cls):                 # the name you pass to .format("metar")
        return "metar"
    def schema(self):              # the columns every row has
        return SCHEMA
    def reader(self, schema):      # used by spark.read (batch)
        return MetarBatchReader(self.options)
    def simpleStreamReader(self, schema):  # used by spark.readStream
        return MetarStreamReader(self.options)
```

The stream reader keeps an **offset**: the last observation time it has seen for each station. Every micro-batch polls aviationweather.gov once and returns only reports newer than the offset. Spark stores the offset in the pipeline checkpoint, so a restart picks up where it left off.

If the live source is down, the reader returns synthetic observations instead, marked `source = 'synthetic'`.

## 3. Declare the streaming table

Replace the contents of the starter file in `transformations/` (rename it to `01_bronze_metar_live.py`) with:

```python
from pyspark import cloudpickle
from pyspark import pipelines as dp

from utilities import metar_source
from utilities.metar_source import DEFAULT_STATIONS, MetarDataSource

# Spark runs the data source in a separate Python worker that can't see the pipeline's
# utilities/ folder. Pickling the module by value ships its code to that worker.
cloudpickle.register_pickle_by_value(metar_source)
spark.dataSource.register(MetarDataSource)

STATIONS = spark.conf.get("lab.stations", DEFAULT_STATIONS)
MODE = spark.conf.get("lab.metar_mode", "auto")


@dp.table(
    name="bronze_metar_live",
    comment="Live METAR observations for Southwest airports (aviationweather.gov). One row per new report.",
)
@dp.expect_or_drop("has_station", "station_id IS NOT NULL")
@dp.expect_or_drop("has_observation_time", "observation_time IS NOT NULL")
@dp.expect("live_not_synthetic", "source <> 'synthetic'")
def bronze_metar_live():
    return (
        spark.readStream.format("metar")
        .option("stations", STATIONS)
        .option("mode", MODE)
        .load()
    )
```

About `register_pickle_by_value`: without it, the run fails with `No module named 'utilities'`. Spark calls the data source from a separate Python worker process, and that process only has installed packages on its path. The original blog avoids this by installing its OpenSky source as a pip package. Shipping the module by value lets you keep the source in your pipeline folder and edit it there.

Compare with the original blog. Only the format name and options change:

```python
spark.readStream.format("opensky").load()     # blog
spark.readStream.format("metar").load()       # this lab
```

Click **Run pipeline**. When the run finishes:
- The **pipeline graph** shows one node, `bronze_metar_live`. Click it.
- **Data preview:** one row per airport, with `raw_text` holding the original METAR.
- **Data quality:** the three expectations and how many rows passed each.

Click **Run pipeline** again. This time `bronze_metar_live` writes zero or only a few rows: just the airports that have filed a new report since the last run. That is the offset at work.

## 4. Load the raw files with Auto Loader

1. Open the pipeline **Settings** (gear icon) → **Configuration** → **Add configuration**:
   - Key `lab.raw_path`, value your `raw_path` from Lab 0. Save.
2. In `transformations/`, create `02_bronze_files.sql` and paste the contents of `src/pipeline/transformations/02_bronze_files.sql`.

What it declares:
- `bronze_bts_flights` and `bronze_weather_history` — streaming tables over `STREAM read_files(...)`. Each new CSV dropped in the folder is picked up once.
- `dim_airports` — a materialized view over the airport reference file.

`${lab.raw_path}` is replaced with the configuration value when the pipeline runs. `_metadata.file_path` records which file each row came from.

Run the pipeline. The graph now has four nodes. `bronze_bts_flights` should have about 362,000 rows (three months of Southwest flights).

## 5. Build the silver layer

Create `transformations/03_silver.sql` and paste the contents of `src/pipeline/transformations/03_silver.sql`. Read the three tables:

| Table | Type | What it does |
|---|---|---|
| `silver_flights` | Streaming table | Typed columns, readable names, departure hour. Expectations drop rows without a date, airport, or valid hour, and count rows missing a delay value. |
| `silver_weather_hourly` | Materialized view | One report per airport per hour. Derives cloud ceiling and FAA flight category (VFR/MVFR/IFR/LIFR), plus thunderstorm and high-wind flags. |
| `silver_metar_latest` | Materialized view | The most recent live report per airport. |

Notice `FROM STREAM(bronze_bts_flights)` in `silver_flights`: reading a streaming table as a stream keeps the silver table incremental too. The two materialized views read with a plain `FROM`.

Run the pipeline. Then click `silver_flights` → **Data quality**. The `delay_reported` expectation is a warning (no `ON VIOLATION`). It reports how many flights have no departure delay, but keeps those rows.

## 6. Look at what you built

Open the **SQL editor** (left sidebar), choose a SQL warehouse, and run:

```sql
USE temp_ai_training_2026.<you>;

SELECT flight_category, COUNT(*) AS hours
FROM silver_weather_hourly
GROUP BY ALL ORDER BY hours DESC;

SELECT origin, ROUND(100 * AVG(CAST(dep_delayed_15 AS INT)), 1) AS pct_delayed
FROM silver_flights
GROUP BY ALL ORDER BY pct_delayed DESC;
```

## Checkpoint

- [ ] The pipeline graph shows 7 tables: 3 bronze, `dim_airports`, 3 silver
- [ ] A second run writes only new rows to `bronze_metar_live` and nothing new to `bronze_bts_flights`
- [ ] You can explain the difference between a streaming table and a materialized view

**Optional:** in the pipeline settings, add `lab.metar_mode` = `synthetic` and run again. The `live_not_synthetic` expectation now flags every new row. Set it back to `auto` when you're done.

Next: [Lab 2 — Extend and debug with Genie Code](02-genie-code.md)
