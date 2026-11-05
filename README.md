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

## Missions

| # | Mission | You learn | Time |
|---|---|---|---|
| 0 | [Get your bearings and set up](labs/00-setup.md) | Where things are, schema and volume, raw files | 15 min |
| 1 | [Stream live weather](labs/01-live-stream.md) | Pipelines Editor, streaming tables, custom data sources, Genie Code | 25 min |
| 2 | [Bring in history and clean it](labs/02-history.md) | Auto Loader, materialized views, pipeline configuration, prompting with context | 30 min |
| 3 | [Join weather to flights, add quality rules](labs/03-join-quality.md) | Joins, expectations, fixing failures with Genie Code | 25 min |
| 4 | [Keep it live](labs/04-keep-it-live.md) | Scheduled vs continuous pipelines, freshness and cost | 10 min |
| 5 | [Rebuild the dashboard with AI](labs/05-dashboard.md) | AI/BI dashboards with Genie Code, publishing, refresh schedules, Tableau migration | 30 min |
| 6 | [Decide where Genie lives](labs/06-genie.md) | Dashboard Genie vs standalone Genie agent vs Genie in an app | 20 min |
| 7 | [Build an app with Genie App Builder](labs/07-app.md) | Genie App Builder, App Spaces, user authorization, sharing | 30 min |
| — | [Wrap-up](labs/08-wrap-up.md) | Show and tell, patterns, cleanup | 10 min |

Each mission gives a goal, a "done when" test, prompt ingredients (not finished prompts), and a hint ladder. Learners write their own prompts.

**Self-service help**
- `labs/check_progress` — notebook that checks each learner's work (by pattern, not by exact names) and gives a hint for each unmet check.
- `@swa-lab-coach` — a Genie Code skill installed for each learner by the setup notebook. Gives hints, not answers.
- `AGENTS.md` — context Genie Code reads automatically when working in the lab folder (data dictionary, definitions, conventions).
- Reference solution: `src/pipeline/` (pipeline) and `app/` (pro-code app).

## Prerequisites

- Access to a Databricks workspace with serverless compute, Unity Catalog, and Databricks Apps (swa-dev for SWA participants)
- `USE CATALOG` and `CREATE SCHEMA` on the lab catalog (`temp_ai_training_2026` on swa-dev)
- `CAN USE` on a SQL warehouse
- Genie Code with partner-powered AI features enabled (Missions 1–5)
- Genie App Builder: the *Governed agentic app-building* preview and a lab App Space (Mission 7). See the instructor guide.

## Instructors

See [docs/INSTRUCTOR.md](docs/INSTRUCTOR.md) for the one-command reference deployment, the shared data copy, and cleanup.

## Repo layout

```
AGENTS.md                 Context Genie Code reads automatically
labs/                     Missions, check_progress notebook, coach skill, assets
src/setup/00_setup.py     Mission 0 notebook: schema, volume, raw files, my_pipeline/, coach skill
src/pipeline/             Finished pipeline (root folder for the Lakeflow Pipelines Editor)
  utilities/metar_source.py     Custom PySpark data source (batch + streaming)
  transformations/              Bronze, silver, gold
app/                      Reference Streamlit app (pro-code fallback for Mission 7)
resources/, databricks.yml      Bundle definition (`databricks bundle`) for the reference deployment
docs/INSTRUCTOR.md        Instructor guide
```

## Data notes

- BTS data is published about two months after the fact. Live weather is current; flight history is not. The live board compares current weather with how Southwest performed historically in the same conditions, not with today's flights.
- Weather history is joined to each flight using the routine report in effect at the scheduled departure hour (a 14:53 report covers departures 15:00–15:59, origin local time).
- Flight category follows FAA definitions: LIFR (ceiling < 500 ft or visibility < 1 mi), IFR (< 1,000 ft or < 3 mi), MVFR (≤ 3,000 ft or ≤ 5 mi), VFR otherwise.
- If aviationweather.gov is unreachable, the data source falls back to synthetic observations (`source = 'synthetic'`) so the lab still runs. The `live_not_synthetic` expectation counts these rows.
