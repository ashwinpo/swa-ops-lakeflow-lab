# Mission 4 — Keep it live

**Time:** 10 min (then it runs in the background) · **You'll use:** Lakeflow Pipelines Editor, Jobs & Pipelines

## The situation

Right now your pipeline only updates when you click Run. The old dashboard refreshed nightly. Ops wants better than that, but they don't need sub-second updates: weather reports arrive every few minutes.

## Your goal

Make the pipeline update on its own, and choose how often. Then add a **live summary**: current conditions at each Southwest airport next to the historical delay rate for those conditions.

## Decide first

| Option | How | Good for | Cost |
|---|---|---|---|
| **Triggered on a schedule** | Pipeline editor → **Schedule** → every N minutes | Data that arrives every few minutes; most dashboards | Pays only while each update runs |
| **Continuous** | Pipeline settings → pipeline mode **Continuous** | Seconds-level freshness | Compute runs all the time |

Pick one for your pipeline and write down why. (For weather, every 5–15 minutes is plenty. Please don't leave a continuous pipeline running after the session.)

## Prompt ingredients for the live summary

Join your **latest report per airport** (from the live stream) to your **historical summary** from Mission 3 on airport and flight category. Show clear-weather delay rate alongside, so Ops sees the difference. Limit it to the 20 airports in `reference/airports.csv`, and include their coordinates; you'll want a map in Mission 5.

## Done when

- Your pipeline has a schedule (or is continuous), and Jobs & Pipelines shows at least one run you didn't start.
- The live streaming table keeps growing between runs. Note its row count, wait one schedule interval, check again.
- `check_progress`: **Mission 4** checks pass.

## Stuck?

<details><summary>Hint 1</summary>

The **Schedule** button is in the pipeline editor's top bar. It creates a job that runs the pipeline.
</details>

<details><summary>Hint 2</summary>

Live station IDs have a `K` prefix (`KDAL`), history uses `DAL`. Pick the latest report per station with `ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY observation_time DESC)`.
</details>

<details><summary>Hint 3</summary>

`silver_metar_latest` in `03_silver.sql` and `gold_live_delay_risk` in `04_gold.sql`.
</details>

Next: [Mission 5 — Rebuild the dashboard with AI](05-dashboard.md)
