# Lab 3 — Ask questions with Genie

**Goal:** give people who don't write SQL a way to ask questions of your gold tables in plain English.

Genie Code (Lab 2) is for builders. A **Genie space** is for everyone else: business users ask questions, and Genie answers with SQL they can inspect, tables, and charts. It uses the tables, descriptions, and instructions you give it, and it follows Unity Catalog permissions.

## 1. Create the space

1. In the left sidebar, click **Genie** → **New**.
2. Add these tables from `temp_ai_training_2026.<you>`:
   - `gold_flights_weather`
   - `gold_delay_by_weather`
   - `gold_airport_daily`
   - `gold_live_delay_risk`
   - `dim_airports`
3. Choose a SQL warehouse and click **Create**.
4. Rename the space `<you> — SWA weather and delays`.

The table and column comments you wrote in the pipeline are already visible to Genie. That is one reason the pipeline files include `COMMENT` clauses.

## 2. Add instructions

Open **Configure** → **Instructions** and paste:

```
- "Delayed" means departure delay of 15 minutes or more (dep_delayed_15), the US DOT standard,
  unless the user asks for another threshold.
- Flight categories, from best to worst weather: VFR, MVFR, IFR, LIFR. "Bad weather" means IFR or LIFR.
- Airports are Southwest stations identified by 3-letter codes (DAL, MDW, BWI...). Use dim_airports
  for names and cities.
- Flight history covers June–August 2026. Live conditions (gold_live_delay_risk) are current and are
  not joined to current flights.
- Only include groups with at least 100 departures when comparing rates.
- Times in gold_flights_weather are local to the origin airport.
```

## 3. Ask questions

Try these, and click **Show code** on at least two to read the SQL Genie wrote:

1. How many Southwest departures are in the data, by month?
2. What percentage of departures were delayed at each airport? Show a bar chart.
3. How much worse is the delay rate in IFR or LIFR weather than in VFR, by airport?
4. Which airports are reporting IFR or LIFR right now, and what was their historical delay rate in those conditions?
5. What were the five worst days at Chicago Midway, and what was the weather?
6. Plot the airports on a map colored by their current flight category.

When an answer is right, click **Save as trusted** (or add it under **Configure** → **SQL queries**). When it's wrong, fix the SQL, save the corrected version, and ask again.

## 4. Share it

Click **Share** and give a teammate **Can run**. They need `SELECT` on your tables for answers to work. Genie doesn't bypass Unity Catalog.

## Checkpoint

- [ ] Your Genie space answers questions 1–6
- [ ] You saved at least one trusted query

Next: [Lab 4 — Ship an app](04-app.md)
