# Lab 2 — Extend and debug with Genie Code

**Goal:** use Genie Code, the AI agent built into the workspace, to build the gold layer, fix a broken pipeline, and write analysis SQL.

Genie Code works inside the Lakeflow Pipelines Editor, notebooks, and the SQL editor. In the pipeline editor it can read your files, search tables, create and edit files, and run the pipeline. It asks for approval before it changes files or runs anything, and it can only touch data you already have access to.

## Before you start

- Open your pipeline from Lab 1 in the Lakeflow Pipelines Editor.
- Click **Genie Code** in the upper-right corner to open the side panel.
- Stay on this browser tab while Genie Code is working. It pauses if you switch away.

**Prompting tips**
- Name the tables and columns you mean. Genie Code reads your files, but being specific saves a round trip.
- Say what file to put the change in.
- Review every diff before you accept it. You own the code.
- When asked to run something, use **Allow** for now. Save **Always allow** for when you trust the pattern.

---

## 1. Ask for an explanation

Prompt:

```
Explain this pipeline. For each table, tell me whether it is a streaming table or a
materialized view, what it reads from, and why that type was chosen.
```

Check the answer against what you learned in Lab 1. Then ask a follow-up:

```
How does bronze_metar_live avoid writing the same weather report twice?
```

The answer should point to the per-station offset in `utilities/metar_source.py`.

## 2. Generate the gold layer

Prompt:

```
Create transformations/04_gold.sql with a materialized view gold_flights_weather.
Join silver_flights to silver_weather_hourly on origin = airport, flight_date = obs_date,
and sched_dep_hour = obs_hour (left join, keep all flights). Include all flight columns
plus flight_category, thunderstorm, high_wind, visibility_mi, ceiling_ft, wind_kt, gust_kt,
wx_codes. Only keep flights whose origin is in dim_airports. Add a table comment.
```

Review the diff, accept it, and let Genie Code run the pipeline (or run it yourself).

Next prompt, in the same chat:

```
In the same file add two materialized views:
1. gold_delay_by_weather: by origin airport, flight_category and thunderstorm — departures,
   average departure delay, % of departures delayed 15+ minutes, % cancelled, average taxi out.
   Exclude rows where flight_category is null. Round percentages to 1 decimal.
2. gold_airport_daily: by origin airport and flight_date — departures, % delayed 15+,
   % cancelled, average departure delay, flights with any weather delay, departures in IFR or
   LIFR, departures in thunderstorms.
Then run the pipeline.
```

Compare the result with `src/pipeline/transformations/04_gold.sql` in your lab folder. Column names may differ; that's fine as long as the logic matches. If you want your app in Lab 4 to work unchanged, ask Genie Code to rename columns to match the reference file:

```
Rename the columns in gold_delay_by_weather and gold_airport_daily to match
/Workspace/Users/<you>/swa-ops-lakeflow-lab/src/pipeline/transformations/04_gold.sql
```

Last gold table. This one joins live data with history, so paste it from the reference file rather than generating it: copy the `gold_live_delay_risk` statement from `src/pipeline/transformations/04_gold.sql` to the end of your `04_gold.sql`. Then ask:

```
Explain what gold_live_delay_risk computes and what delay_pts_vs_clear means.
```

## 3. Fix a failure

Break something on purpose. In `03_silver.sql`, change `AS sched_dep_hour` to `AS sched_departure_hour` and run the pipeline. The update fails because `gold_flights_weather` still uses the old name.

Prompt:

```
Fix the failure in this pipeline.
```

Watch what Genie Code does: it reads the error, finds every place the column is used, and proposes a fix. It might rename the column back or update the downstream query. Either is valid. Pick one and say why in the chat.

## 4. Add a data quality rule

Prompt:

```
Add an expectation to silver_flights that warns (does not drop) when taxi_out_min is
greater than 90. Run the pipeline and tell me how many rows violate it, by origin airport.
```

Open `silver_flights` → **Data quality** to confirm the new expectation and its counts.

## 5. Analyze in the SQL editor

Open the **SQL editor** in a new tab and open its Genie Code panel. Set the catalog and schema to yours.

```
Using gold_flights_weather, which three airports have the largest increase in
% departures delayed 15+ when the weather is IFR or LIFR compared with VFR?
Only include airports with at least 200 IFR or LIFR departures.
```

Run the generated query and check that the filter on 200 departures is there. Then:

```
Now break that down by hour of the day for the top airport. Which hours are worst?
```

**Save this query** (name it `ifr_delay_lift`). You will put a version of it in your app in Lab 4.

## Checkpoint

- [ ] Your pipeline has the four gold tables and runs without errors
- [ ] You fixed a broken run with Genie Code and reviewed the change
- [ ] You have a saved SQL query that compares IFR/LIFR with VFR delays

## Going further

- Ask Genie Code to add a route-level table: `gold_route_delays` by `route` and `flight_category`.
- Ask: *"Is gold_delay_by_weather refreshed incrementally or with a full recompute? Why?"* Genie Code can read the pipeline's incrementalization details and suggest query changes.
- Add workspace instructions for Genie Code (Settings → Genie Code → Instructions) with your team's SQL conventions, then repeat a prompt and compare.

Next: [Lab 3 — Ask questions with Genie](03-genie-space.md)
