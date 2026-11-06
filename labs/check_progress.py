# Databricks notebook source
# MAGIC %md
# MAGIC # Check my progress
# MAGIC
# MAGIC Run this notebook (serverless) any time. It looks at what you've built in your schema and workspace and
# MAGIC tells you which missions are done. It doesn't care what you named things or exactly how you built them —
# MAGIC it checks the *patterns*: is there a streaming table, is it getting new data, is there a dashboard on it, and so on.
# MAGIC
# MAGIC When a check isn't passing, read the hint next to it. Still stuck? Ask Genie Code: `@swa-lab-coach I'm stuck on mission 2`.

# COMMAND ----------

dbutils.widgets.text("catalog", "temp_ai_training_2026", "Catalog")
dbutils.widgets.text("schema", "", "Schema (blank = your username)")

import json, os, re
from datetime import datetime, timedelta, timezone

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me().user_name
catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip() or re.sub(r"[^a-z0-9]+", "_", me.split("@")[0].lower()).strip("_")
fq = f"`{catalog}`.`{schema}`"
now = datetime.now(timezone.utc)
recent = now - timedelta(days=21)

results = []   # (mission, check, passed, detail, hint)


def check(mission, name, passed, detail="", hint=""):
    parts = [x.strip() for x in str(detail).split(",")]
    if len(parts) > 3:
        detail = ", ".join(parts[:3]) + f", +{len(parts) - 3} more"
    results.append((mission, name, bool(passed), detail, hint))
    return bool(passed)


def q(sql):
    return spark.sql(sql).collect()

# COMMAND ----------

# --- What's in the schema -----------------------------------------------------------------------
tables, columns = {}, {}
try:
    for r in q(f"SELECT table_name, table_type FROM `{catalog}`.information_schema.tables "
               f"WHERE table_schema = '{schema}' AND table_name NOT LIKE '\\_\\_%'"):
        tables[r.table_name] = r.table_type
    for r in q(f"SELECT table_name, lower(column_name) AS c, lower(data_type) AS t "
               f"FROM `{catalog}`.information_schema.columns WHERE table_schema = '{schema}' "
               f"AND table_name NOT LIKE '\\_\\_%'"):
        columns.setdefault(r.table_name, {})[r.c] = r.t
except Exception as e:
    print(f"Could not read {catalog}.{schema}: {e}")


def find(kind=None, has_all=(), has_any=()):
    """Tables of a type whose columns include all of has_all and at least one of has_any."""
    out = []
    for t, cols in columns.items():
        if kind and tables.get(t) != kind:
            continue
        if all(c in cols for c in has_all) and (not has_any or any(c in cols for c in has_any)):
            out.append(t)
    return sorted(out)


def count(t):
    try:
        return q(f"SELECT COUNT(*) AS n FROM {fq}.`{t}`")[0].n
    except Exception:
        return 0

# COMMAND ----------

# --- Mission 0: setup ---------------------------------------------------------------------------
raw = f"/Volumes/{catalog}/{schema}/raw"
have = {d: os.path.isdir(f"{raw}/{d}") and len(os.listdir(f"{raw}/{d}")) for d in ["bts", "weather_history", "reference"]}
check(0, "Raw files loaded into your volume", all(have.values()), str(have),
      "Run src/setup/00_setup (Lab 0) on serverless.")

# --- Mission 1: live stream ---------------------------------------------------------------------
live = find("STREAMING_TABLE", has_all=("station_id", "observation_time"))
check(1, "A streaming table reads live weather", live, ", ".join(live),
      "Create a pipeline and declare a streaming table with spark.readStream.format('metar'). See labs/01-live-stream.md.")
live_t = live[0] if live else None
if live_t:
    n = count(live_t)
    check(1, "It has data", n > 0, f"{n:,} rows in {live_t}", "Run the pipeline.")
    cols = columns[live_t]
    if "ingest_time" in cols:
        stats = q(f"SELECT COUNT(DISTINCT date_trunc('MINUTE', ingest_time)) AS runs, MAX(ingest_time) AS last, "
              f"COUNT(DISTINCT station_id) AS stations FROM {fq}.`{live_t}`")[0]
        check(1, "It picked up new reports on a second run (incremental)", stats.runs >= 2,
              f"data from {stats.runs} separate runs", "Run the pipeline again a few minutes later. Only new reports should be added.")
        check(1, "Bonus: streaming every US station", stats.stations > 500, f"{stats.stations:,} stations",
              "Read the docstring at the top of utilities/metar_source.py. One option widens the feed.")
    else:
        stats = None

# --- Mission 2: history + clean -----------------------------------------------------------------
flights_raw = find("STREAMING_TABLE", has_any=("flightdate",))
check(2, "Flight files ingested with Auto Loader (streaming table)", flights_raw, ", ".join(flights_raw),
      "Use read_files(...) with STREAM over the bts/ folder in your volume.")
wx_raw = find("STREAMING_TABLE", has_all=("station", "valid"))
check(2, "Weather history ingested with Auto Loader", wx_raw, ", ".join(wx_raw),
      "Same pattern as flights, over weather_history/.")
clean = [t for t in find(has_all=("origin",)) + find(has_all=("dest",))
         if any(v == "date" for v in columns[t].values()) and t not in flights_raw]
check(2, "A cleaned flights table with typed columns", clean, ", ".join(sorted(set(clean))),
      "Raw columns are strings like '0545' and '2026-06-01'. Ask Genie Code to clean them into a new table.")
wx_clean = find(has_any=("flight_category",))
check(2, "Weather categorized (VFR/MVFR/IFR/LIFR)", wx_clean, ", ".join(wx_clean),
      "Derive a flight category from ceiling and visibility. Definitions are in labs/02-history.md.")

# --- Mission 3: join + quality ------------------------------------------------------------------
joined = [t for t in find(has_any=("flight_category",)) if any(c in columns[t] for c in ("origin", "dep_delay_min", "depdelay", "dep_delay"))]
check(3, "Flights joined to the weather at departure", joined, ", ".join(joined),
      "Join on airport, date, and departure hour. Which hour's report applies to a 3:20 pm departure?")

pipelines = []
for p in w.pipelines.list_pipelines():
    if p.creator_user_name != me:
        continue
    try:
        spec = w.pipelines.get(p.pipeline_id).spec
    except Exception:
        continue
    if spec and spec.catalog == catalog and (spec.schema == schema or spec.target == schema):
        pipelines.append((p.pipeline_id, p.name, spec))
check(3, "Your pipeline found", pipelines, ", ".join(n for _, n, _ in pipelines),
      f"Set the pipeline's default catalog/schema to {catalog}.{schema}.")

n_expect = 0
for pid, _, _ in pipelines:
    try:
        n_expect = max(n_expect, q(f"""
            SELECT COUNT(DISTINCT e.name) AS n
            FROM event_log('{pid}')
            LATERAL VIEW explode(from_json(details:flow_progress:data_quality:expectations,
                                 'array<struct<name:string>>')) x AS e
            WHERE event_type = 'flow_progress'""")[0].n)
    except Exception:
        pass
check(3, "Data quality expectations in the pipeline (3+)", n_expect >= 3, f"{n_expect} expectations",
      "Add rules with CONSTRAINT ... EXPECT (SQL) or @dp.expect (Python). Decide: warn, drop, or fail?")

# --- Mission 4: keep it live --------------------------------------------------------------------
scheduled = False
for pid, _, spec in pipelines:
    if spec.continuous:
        scheduled = True
for j in w.jobs.list(expand_tasks=True):
    if j.creator_user_name != me or not j.settings:
        continue
    s = j.settings
    runs_pipeline = any(t.pipeline_task and t.pipeline_task.pipeline_id in [p[0] for p in pipelines] for t in (s.tasks or []))
    active = (s.schedule and str(s.schedule.pause_status) != "PauseStatus.PAUSED") or s.continuous or s.trigger
    if runs_pipeline and active:
        scheduled = True
check(4, "Pipeline runs on a schedule (or continuously)", scheduled, "",
      "In the pipeline editor: Schedule. Every 5–15 minutes is plenty for weather.")
if live_t and "ingest_time" in columns[live_t]:
    last = stats.last.replace(tzinfo=timezone.utc) if stats and stats.last else None
    fresh = last and now - last < timedelta(minutes=30)
    check(4, "Live data is fresh (< 30 min old)", fresh, f"last ingest {last:%H:%M} UTC" if last else "",
          "Has your schedule run yet? Check Jobs & Pipelines → your job → Runs.")

# COMMAND ----------

# --- Mission 5: dashboard -----------------------------------------------------------------------
dashboards = []
for d in w.lakeview.list():
    if d.create_time and datetime.fromisoformat(d.create_time.replace("Z", "+00:00")) < recent:
        continue
    try:
        full = w.lakeview.get(d.dashboard_id)
    except Exception:
        continue
    if full.serialized_dashboard and schema in full.serialized_dashboard and (full.path or "").startswith(f"/Users/{me}"):
        dashboards.append(full)
check(5, "An AI/BI dashboard on your tables", dashboards, ", ".join(d.display_name for d in dashboards),
      "New → Dashboard, then describe what you want to Genie Code. Reference tables with @.")
widgets, published, sched, uses_live = 0, False, False, False
for d in dashboards:
    sd = json.loads(d.serialized_dashboard)
    widgets = max(widgets, sum(len(p.get("layout", [])) for p in sd.get("pages", [])))
    uses_live = uses_live or bool(live_t and live_t in d.serialized_dashboard) or "metar" in d.serialized_dashboard.lower()
    try:
        w.lakeview.get_published(d.dashboard_id)
        published = True
    except Exception:
        pass
    try:
        sched = sched or any(True for _ in w.lakeview.list_schedules(d.dashboard_id))
    except Exception:
        pass
check(5, "Dashboard has 4+ widgets", widgets >= 4, f"{widgets} widgets", "Match the panels on the legacy Tableau mock.")
check(5, "Dashboard shows live data", uses_live, "",
      "At least one widget should read the live weather (your streaming table or something built on it).")
check(5, "Dashboard published (Genie is on by default)", published, "", "Click Publish, choose a data permission, then View published.")
check(5, "Dashboard refresh schedule", sched, "",
      "Dashboards cache results. Without a schedule, new pipeline data won't show up on its own. Schedule → Add schedule.")

# --- Mission 6: Genie ---------------------------------------------------------------------------
spaces, token = [], None
for _ in range(10):
    resp = w.api_client.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
    for s in resp.get("spaces", []):
        if s.get("create_time", "") >= recent.isoformat()[:19]:
            spaces.append(s)
    token = resp.get("next_page_token")
    if not token:
        break
mine = []
for s in spaces[:150]:
    try:
        full = w.api_client.do("GET", f"/api/2.0/genie/spaces/{s['space_id']}", query={"include_serialized_space": "true"})
        if schema in (full.get("serialized_space") or ""):
            mine.append(s["title"])
    except Exception:
        pass
check(6, "Genie is answering questions on your data", mine or published,
      ("standalone: " + ", ".join(mine)) if mine else ("dashboard Genie (published dashboard)" if published else ""),
      "Either publish your dashboard with Enable Genie on, or create a standalone Genie agent. Mission 6 asks you to pick and explain why.")

# --- Mission 7: app -----------------------------------------------------------------------------
apps = [a for a in w.apps.list()
        if a.creator == me and a.create_time and datetime.fromisoformat(a.create_time.replace("Z", "+00:00")) >= recent]
running = [a for a in apps if a.compute_status and "ACTIVE" in str(a.compute_status.state)]
check(7, "You built an app", apps, ", ".join(a.name for a in apps), "App switcher (9-dot grid) → Databricks Apps → Build. See labs/07-app.md.")
check(7, "It's running", running, ", ".join(a.url or a.name for a in running), "Open the app page and click Start, or Deploy.")

# COMMAND ----------

MISSIONS = {0: "Setup", 1: "Live stream", 2: "History + clean", 3: "Join + quality",
            4: "Keep it live", 5: "Dashboard", 6: "Genie", 7: "App (optional)"}
CORE = [m for m in MISSIONS if m != 7]
lines, done_missions = [], 0
for m, title in MISSIONS.items():
    rows = [r for r in results if r[0] == m]
    required = [r for r in rows if not r[1].startswith("Bonus")]
    ok = required and all(r[2] for r in required)
    done_missions += bool(ok) and m in CORE
    lines.append(f"\nMission {m} — {title}: {'DONE' if ok else 'in progress'}")
    for _, name, passed, detail, hint in rows:
        mark = "[x]" if passed else "[ ]"
        lines.append(f"  {mark} {name}" + (f"  ({detail})" if detail else ""))
        if not passed and hint:
            lines.append(f"        hint: {hint}")

rank = ["Ground crew", "Ground crew", "Ramp agent", "Dispatcher", "Dispatcher", "First officer", "First officer", "Captain"][done_missions]
app_done = all(r[2] for r in results if r[0] == 7)
if done_missions == len(CORE) and app_done:
    rank = "Chief pilot"
report = f"{me}  ·  {catalog}.{schema}  ·  {done_missions}/{len(CORE)} core missions done  ·  rank: {rank}\n" + "\n".join(lines)
print(report)
dbutils.notebook.exit(report)
