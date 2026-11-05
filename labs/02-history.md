# Mission 2 — Bring in history and clean it

**Time:** 30 min · **You'll use:** Lakeflow Pipelines Editor, Genie Code, Catalog

## The situation

Live weather tells you what's happening now. To say what it *means* for Southwest, you need history: three months of Southwest flights (BTS on-time data) and hourly weather at 20 airports over the same months. Those files are in your volume from Mission 0. They're raw: times like `0545`, `M` for missing, cloud layers spread over six columns.

## Your goal

Add to your pipeline:
1. Two **streaming tables** that load the flight CSVs and the weather history CSVs from your volume with **Auto Loader**.
2. **Cleaned** versions: typed columns (dates are dates, numbers are numbers), readable names, a scheduled departure **hour** for each flight.
3. A **flight category** (VFR, MVFR, IFR, LIFR) for every hourly weather report.

## Key ideas

- **Auto Loader** (`read_files` with `STREAM`) picks up new files in a folder and processes each file once. Drop a new month in `bts/` and only that file is read next run.
- **Materialized view** = a table defined by a query that the pipeline keeps up to date. Use it when you need to look across all rows (dedupe, join, aggregate). A streaming table only sees each new row once.
- You can mix SQL and Python files in one pipeline.

## What you need to know

- Your raw path: `/Volumes/temp_ai_training_2026/<you>/raw` with `bts/`, `weather_history/`, `reference/airports.csv`.
- Set it once as a pipeline **configuration** value (pipeline **Settings** → **Configuration**, e.g. key `lab.raw_path`) so your code doesn't hard-code it. SQL can reference it as `${lab.raw_path}`.
- **Flight category** (FAA): LIFR if ceiling < 500 ft or visibility < 1 mi; IFR if < 1,000 ft or < 3 mi; MVFR if ≤ 3,000 ft or ≤ 5 mi; otherwise VFR. **Ceiling** = the lowest cloud layer that is BKN, OVC, or VV.
- Weather history `valid` is local time at the airport, the same as BTS scheduled times.

## Prompt ingredients

You'll get better results if you:
- Name the **folder**, the **format**, and the **table type** you want ("streaming table with Auto Loader from `${lab.raw_path}/bts`").
- Say what's **wrong** with the raw data and what "clean" means to you. You saw the files in Mission 0.
- Ask Genie Code to **look at the data first** ("sample the bronze table and suggest cleaning steps") before it writes the cleaning code.
- Do one table at a time, and **run and look** after each.

## Done when

- The graph shows raw flights and raw weather streaming tables, plus cleaned tables downstream of them.
- Your cleaned flights table has a date column, an origin airport, a departure hour (0–23), and numeric delay columns. About 362,000 flights.
- Every weather hour has a flight category. Run in the SQL editor: count reports by category. Most hours should be VFR.
- `check_progress`: **Mission 2** checks pass.

## Stuck?

<details><summary>Hint 1 — where to look</summary>

Catalog → your table → **Sample data** shows what actually landed. If a column you expect isn't there, check the CSV header in the volume.
</details>

<details><summary>Hint 2 — an approach</summary>

Bronze: `CREATE OR REFRESH STREAMING TABLE ... AS SELECT * FROM STREAM read_files('${lab.raw_path}/bts', format => 'csv', header => true)`. Silver: read the bronze table with `STREAM(...)` for a streaming table, or plain `FROM` for a materialized view. For ceiling, `least()` over three `CASE WHEN skycN IN ('BKN','OVC','VV') THEN skylN END` expressions works; `least` skips nulls.
</details>

<details><summary>Hint 3 — compare with the reference</summary>

`src/pipeline/transformations/02_bronze_files.sql` and `03_silver.sql`.
</details>

## Reflect

- Open `AGENTS.md` at the top of your lab folder. Genie Code reads it automatically. How did it change what Genie Code wrote? What would you put in an `AGENTS.md` for your own team's data?
- Which of your silver tables are streaming tables and which are materialized views? Why?

Next: [Mission 3 — Join weather to flights and add quality rules](03-join-quality.md)
