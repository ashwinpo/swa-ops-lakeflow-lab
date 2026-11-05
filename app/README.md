# Reference app (pro-code path)

The lab builds its app with Genie App Builder (Mission 7). This Streamlit app is the reference version, and the fallback when Genie App Builder isn't available.

It reads `gold_live_delay_risk`, `gold_delay_by_weather`, and `gold_airport_daily` from the reference pipeline (`src/pipeline/`). If your tables have different names, edit the queries in `app.py`.

## Deploy from the UI

1. **Apps** → **Create app** → **Create a custom app**. Name it `<you>-ops-board` (lowercase, hyphens, 30 characters max).
2. **App resources** → **Add resource** → **SQL warehouse**, permission **Can use**, resource key `sql-warehouse` (must match `app.yaml`).
3. **User authorization** → **Add scope** → `sql`.
4. **Create app**, then **Deploy** from the folder `/Workspace/Users/<you>/swa-ops-lakeflow-lab/app`.

The app queries as the signed-in user (`X-Forwarded-Access-Token`), so viewers need `SELECT` on the schema. The schema defaults to the viewer's username; set `LAB_SCHEMA` in `app.yaml` to pin it.

## Deploy with the bundle

`databricks bundle run ops_board -p <profile>` (see `docs/INSTRUCTOR.md`).
