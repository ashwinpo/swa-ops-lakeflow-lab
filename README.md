# SWA Ops Lakeflow Lab

A self-paced hands-on lab for Southwest Airlines teams: build a streaming pipeline with **Lakeflow Spark Declarative Pipelines (SDP)**, use **Genie Code** to extend and debug it, and ship a **Databricks App** on top of it.

The lab uses only public data:

| Data | Source | How it arrives |
|---|---|---|
| Live airport weather (METAR) for 20 Southwest airports | NOAA Aviation Weather Center (aviationweather.gov) | Custom PySpark data source, streaming |
| Southwest (WN) flight-level on-time performance, Jun–Aug 2026 | US DOT Bureau of Transportation Statistics | CSV files in a volume, Auto Loader |
| Hourly weather history for the same airports and months | Iowa Environmental Mesonet ASOS archive | CSV files in a volume, Auto Loader |

The question the lab answers: **how much does weather at the departure airport change Southwest's delay rate, and what does that mean for the airports reporting bad weather right now?**

> Adapted from the Databricks blog [Processing millions of events from thousands of aircraft with one declarative pipeline](https://www.databricks.com/blog/processing-millions-events-thousands-aircraft-one-declarative-pipeline). The original reads ADS-B positions from the OpenSky Network. OpenSky drops connections from cloud IP ranges (tested from swa-dev serverless, Nov 2026) and is licensed for non-commercial use only, so this version streams public weather data instead. The custom data source pattern is the same.

## What you build

```
aviationweather.gov ──(custom PySpark data source)──► bronze_metar_live ──► silver_metar_latest ─┐
                                                                                                ├─► gold_live_delay_risk ──► Ops Board app
BTS on-time CSVs ──(Auto Loader)──► bronze_bts_flights ──► silver_flights ──┐                   │
                                                                            ├─► gold_flights_weather ─► gold_delay_by_weather
IEM weather CSVs ──(Auto Loader)──► bronze_weather_history ──► silver_weather_hourly ┘            └─► gold_airport_daily
                                                                                                        │
                                                                                         Genie space ◄──┘
```

## Labs

| # | Lab | You learn | Time |
|---|---|---|---|
| 0 | [Setup](labs/00-setup.md) | Workspace folder, schema, volume, loading raw files | 10 min |
| 1 | [Build the pipeline](labs/01-pipeline.md) | Lakeflow Pipelines Editor, streaming tables, materialized views, expectations, custom data sources, Auto Loader | 40 min |
| 2 | [Extend and debug with Genie Code](labs/02-genie-code.md) | Genie Code in the pipeline editor and SQL editor: explain, generate, fix, review diffs | 30 min |
| 3 | [Ask questions with Genie](labs/03-genie-space.md) | Genie space on the gold tables, instructions, sample questions | 15 min |
| 4 | [Ship an app](labs/04-app.md) | Databricks Apps: create, deploy, user authorization, add a feature | 30 min |

Each lab has a finished version in this repo. If you get stuck, compare with:
- Pipeline: [`src/pipeline/`](src/pipeline/)
- App: [`app/`](app/)

## Prerequisites

- Access to a Databricks workspace with serverless compute, Unity Catalog, and Databricks Apps (swa-dev for SWA participants)
- `USE CATALOG` and `CREATE SCHEMA` on the lab catalog (`temp_ai_training_2026` on swa-dev)
- `CAN USE` on a SQL warehouse
- Genie Code enabled in the workspace (Labs 2–3)

## Instructors

See [docs/INSTRUCTOR.md](docs/INSTRUCTOR.md) for the one-command reference deployment, the shared data copy, and cleanup.

## Repo layout

```
labs/                     Step-by-step instructions
src/setup/00_setup.py     Lab 0 notebook: schema, volume, raw file download
src/pipeline/             Finished pipeline (root folder for the Lakeflow Pipelines Editor)
  utilities/metar_source.py     Custom PySpark data source (batch + streaming)
  transformations/              Bronze, silver, gold
app/                      Finished Streamlit app
resources/, databricks.yml      Bundle definition (`databricks bundle`) for the reference deployment
docs/INSTRUCTOR.md        Instructor guide
```

## Data notes

- BTS data is published about two months after the fact. Live weather is current; flight history is not. The live board compares current weather with how Southwest performed historically in the same conditions, not with today's flights.
- Weather history is joined to each flight using the routine report in effect at the scheduled departure hour (a 14:53 report covers departures 15:00–15:59, origin local time).
- Flight category follows FAA definitions: LIFR (ceiling < 500 ft or visibility < 1 mi), IFR (< 1,000 ft or < 3 mi), MVFR (≤ 3,000 ft or ≤ 5 mi), VFR otherwise.
- If aviationweather.gov is unreachable, the data source falls back to synthetic observations (`source = 'synthetic'`) so the lab still runs. The `live_not_synthetic` expectation counts these rows.
