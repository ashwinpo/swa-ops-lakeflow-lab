# Lab 4 — Ship an app

**Goal:** deploy the Ops Board, a Streamlit app on your gold tables, as a Databricks App. Then add a feature with help from Genie Code.

Databricks Apps run your Python or Node.js code on serverless compute inside the workspace. Users sign in with their workspace identity. Nothing to host, no credentials to manage.

## How the app reads data

`app/app.py` queries a SQL warehouse with the **signed-in user's** identity (user authorization, scope `sql`). Each person sees only the tables they can read in Unity Catalog, and access is audited under their name. The app's own service principal has no access to your tables.

```python
token = st.context.headers.get("X-Forwarded-Access-Token")   # set by Databricks Apps
sql.connect(server_hostname=cfg.host,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            access_token=token)
```

The schema defaults to your username (the same rule as Lab 0), so you don't need to configure it.

## 1. Create the app

1. In the left sidebar, click **Compute** → **Apps** → **Create app** → **Create a custom app**.
2. **Name:** `<you>-ops-board` (lowercase, hyphens, 30 characters max). Click **Next: Configure**.
3. Under **App resources**, click **Add resource** → **SQL warehouse**:
   - Choose the lab warehouse
   - Permission: **Can use**
   - Resource key: `sql-warehouse` (must match `app.yaml`)
4. Under **User authorization**, click **Add scope** → **sql**.
5. Click **Create app**. Wait for the compute to start (1–2 minutes).

## 2. Deploy your code

1. On the app page, click **Deploy**.
2. Choose the folder `/Workspace/Users/<you>/swa-ops-lakeflow-lab/app` and click **Deploy**.
3. When the status shows **Running**, open the app URL. Approve the consent screen; this lets the app query on your behalf.

You should see three tabs:
- **Live conditions** — map and table of current weather at each airport next to the historical delay rate for the same conditions
- **Delay by weather** — delay rates by flight category for the airports you pick
- **Daily performance** — daily delay rate for one airport

If you see *"Could not read ... gold_live_delay_risk"*, check that your pipeline finished and that the schema in the sidebar is yours.

Look at `app/app.yaml` and `app/requirements.txt`. `app.yaml` holds the start command and environment variables; `valueFrom: sql-warehouse` injects the warehouse ID from the resource you added.

## 3. Add a feature

Add a fourth tab, **Bad weather lift**, showing the airports whose delay rate rises the most in IFR/LIFR compared with VFR. This is the query you saved in Lab 2.

1. **Write the SQL with Genie Code.** Open your saved `ifr_delay_lift` query in the SQL editor (or ask Genie Code to write it again). It should return one row per airport with `vfr_pct`, `ifr_pct`, `lift_pts`, and the IFR/LIFR departure count, using `gold_flights_weather`.
2. **Add the tab.** Open `app/app.py` in your workspace folder.
   - Add `"Bad weather lift"` to the `st.tabs([...])` list and a matching variable (`tab_lift`).
   - At the end of the file, add:

     ```python
     with tab_lift:
         lift = query(f"""
             <your SQL here, with tables written as {fq}.gold_flights_weather>
         """)
         st.bar_chart(lift, x="airport", y="lift_pts")
         st.dataframe(lift, hide_index=True, use_container_width=True)
     ```

   Genie Code can help with the Python too. Paste the snippet into the Genie Code panel and ask it to make the chart sort by `lift_pts`, descending.
3. **Redeploy.** On the app page, click **Deploy** again with the same folder. Refresh the app.

## 4. Share it

On the app page, click **Permissions** and give a teammate **Can use**. When they open it, the app queries as *them*, so they see results only if they can read your schema. To let them in, grant read access:

```sql
GRANT USE SCHEMA, SELECT ON SCHEMA temp_ai_training_2026.<you> TO `teammate@wnco.com`;
```

## Checkpoint

- [ ] Your app runs and shows your data
- [ ] You added the **Bad weather lift** tab and redeployed
- [ ] You can explain why the app queries as the signed-in user, not as the app

## Going further

- Turn on the `swa_ops_live_weather_refresh` pattern for your own pipeline: create a job that runs it every 15 minutes, then watch the **Live conditions** tab change over an afternoon.
- Add a Genie conversation to the app with the Genie Conversation API and the `genie` user authorization scope, pointed at your space from Lab 3.

## Clean up

When the training is over:
1. Stop or delete the app (**Compute → Apps**).
2. Delete the pipeline (**Jobs & Pipelines**).
3. Drop your schema: `DROP SCHEMA temp_ai_training_2026.<you> CASCADE;`
