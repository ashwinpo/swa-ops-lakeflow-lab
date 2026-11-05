# Mission 3 — Join weather to flights and add quality rules

**Time:** 25 min · **You'll use:** Lakeflow Pipelines Editor, Genie Code, SQL Editor

## The situation

Ops wants one number they trust: *when the weather at the departure airport is like this, how often is Southwest late?* That needs every flight matched to the weather report in effect when it was scheduled to leave. They also want to know the data is right before they put it in front of the station leaders.

## Your goal

1. A table of **flights with the weather at departure**.
2. A **summary**: % of departures delayed 15+ minutes and % cancelled, by airport and weather condition.
3. At least **three data quality rules** (expectations) in your pipeline, and a decision for each: warn, drop the row, or fail the update.

## The puzzle

A routine weather report is issued at about :53 every hour. Which report applies to a flight scheduled at 3:20 pm? Decide before you prompt. Then tell Genie Code your rule.

## Prompt ingredients

- Say which **two tables** to join, on which **keys** (airport, date, hour), and **what kind of join** (keep flights with no weather match?).
- Ask for the summary as a **materialized view**, and say what to group by and what to compute.
- For quality rules, describe the rule *and* what should happen when it's broken. Example ideas: no flight without a date; departure hour between 0 and 23; flag taxi-out times over 90 minutes; weather reports with no visibility and no ceiling.

## Done when

- Your joined table has a flight category on almost every flight (check: what % of flights have a null category?).
- Your summary answers, in the SQL editor: *How much higher is the delay rate in thunderstorms than in clear weather?*
- Pipeline graph → click a table → **Data quality** shows your rules with pass/fail counts.
- `check_progress`: **Mission 3** checks pass.

## Stuck?

<details><summary>Hint 1</summary>

If almost nothing matches, look at one airport and one day in both tables side by side. Compare the hours.
</details>

<details><summary>Hint 2</summary>

Shift each report forward a few minutes before taking its hour (a 14:53 report → hour 15). Then join on `origin = airport AND flight_date = obs_date AND sched_dep_hour = obs_hour`. Expectations in SQL: `CONSTRAINT name EXPECT (condition) ON VIOLATION DROP ROW` (omit `ON VIOLATION` to only warn).
</details>

<details><summary>Hint 3</summary>

`src/pipeline/transformations/03_silver.sql` (the hour logic) and `04_gold.sql`.
</details>

## Try this: break it on purpose

Rename a column in one of your silver tables and run. The update fails downstream. Ask Genie Code: **"Fix the failure in this pipeline."** Watch how it finds every place the column is used. Did it rename back or update the downstream query? Which would you choose?

## Reflect

- You'll probably find that IFR weather *without* thunderstorms shows a lower delay rate than clear weather. Why might that be? (Think about time of day.) How would you check?

Next: [Mission 4 — Keep it live](04-keep-it-live.md)
