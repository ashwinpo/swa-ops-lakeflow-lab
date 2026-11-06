# Instructor guide

## Before the session

### 1. Permissions participants need

Ask a workspace or metastore admin to grant these to the participant group:

| What | Grant |
|---|---|
| Lab catalog | `USE CATALOG`, `CREATE SCHEMA` on `temp_ai_training_2026` |
| Shared raw files | `USE SCHEMA` and `READ VOLUME` on `temp_ai_training_2026.lab_shared` (after step 3) |
| SQL warehouse | `CAN USE` on the lab warehouse |
| Serverless compute | Serverless notebooks, jobs, and pipelines enabled for the group |
| Genie Code | Partner-powered AI features enabled for the workspace (confirmed on in swa-dev, Nov 2026) |
| Genie App Builder | Workspace preview **Governed agentic app-building** turned on (admin: user menu → Previews), a lab **App Space**, and **CAN CREATE APP** on it for the group |
| App Space resources | Share the lab SQL warehouse to the App Space. Apps run as the signed-in user, so learners read their own schema. |
| Pro-code fallback | Permission to create apps (only if App Builder isn't available) |

```sql
GRANT USE CATALOG, CREATE SCHEMA ON CATALOG temp_ai_training_2026 TO `<participant group>`;
```

### 2. Deploy and test the reference solution

From a clone of this repo, with a CLI profile for the workspace:

```bash
databricks bundle deploy -p <profile>
databricks bundle run setup_and_refresh -p <profile>   # ~10 min: load files, run pipeline
databricks bundle run ops_board -p <profile>           # start the app
```

This creates, in development mode (names prefixed with `dev_<you>_` / `[dev <you>]`):

| Resource | Name |
|---|---|
| Schema + volume | `temp_ai_training_2026.dev_<you>_lab_reference`, volume `raw` |
| Pipeline | `[dev <you>] swa_ops_pipeline` |
| Jobs | `swa_ops_setup_and_refresh`, `swa_ops_live_weather_refresh` (every 15 min, **paused**) |
| App | `swa-ops-board-ref` |

Override variables as needed, e.g. `--var catalog=my_catalog --var app_name=my-ops-board`.

Unpause `swa_ops_live_weather_refresh` during the session if you want the live board to update on its own. Each run is a short serverless pipeline update.

### 3. Load the shared raw files (recommended)

So 30 participants don't each download from BTS and IEM, load one shared copy. Run `src/setup/00_setup` once with:
- `schema` = `lab_shared`
- `shared_schema` = blank

Then grant `USE SCHEMA` and `READ VOLUME` on `temp_ai_training_2026.lab_shared` to participants. Lab 0 copies from `lab_shared` when it exists and downloads otherwise.

### 4. Publish the lab folder

```bash
scripts/publish_to_workspace.sh <profile>     # -> /Workspace/Shared/swa-ops-lakeflow-lab
```

Participants clone this folder into their home folder in Lab 0. Give the participant group `CAN READ` on it.

### 5. Dry run as a learner

Before the session, do Missions 0–7 once with a non-admin account. The bundle tests the code; it doesn't test the clicks. Run `labs/check_progress` at the end; all missions should show DONE.

## How learners get help

1. **Stuck?** hints in each mission (where to look → an approach → the reference file).
2. `@swa-lab-coach` in Genie Code — installed per learner by `00_setup`, gives hints rather than answers. Source: `labs/coach/SKILL.md`.
3. `labs/check_progress` — tells them what's done and gives a hint for each unmet check.
4. A neighbor, then you.

## During the session

Common issues:

| Symptom | Cause / fix |
|---|---|
| `No module named 'utilities'` in the pipeline | Pipeline root folder isn't `my_pipeline/`. Settings → root folder. (`metar_source.py` registers itself for pickling; the root folder just has to be on the path.) |
| No **Build** in Databricks Apps (app switcher) | Governed agentic app-building preview off, or learner not on the App Space. Use the pro-code fallback in Mission 7. |
| Dashboard live panel is stale | Dashboard cache. Add a dashboard schedule, or click Refresh. |
| `lab.raw_path` unresolved / path not found | Pipeline configuration key missing or misspelled. Settings → Configuration. |
| `bronze_metar_live` rows all `source = 'synthetic'` | aviationweather.gov unreachable from serverless at that moment. The lab still works; the expectation counts these rows. |
| App shows "Could not read ... gold_live_delay_risk" | Pipeline not run to completion, or the sidebar schema isn't theirs. |
| App consent screen loops | User authorization scope `sql` missing on the app. |
| Genie Code doesn't offer to edit files | Partner-powered AI features off for the workspace, or user isn't in the pipeline editor tab. |

## After the session

```bash
databricks bundle destroy -p <profile>
```

Then have participants (or an admin) drop their schemas and delete their apps and pipelines. The catalog `temp_ai_training_2026` is marked as safe to delete after the sessions.

## Why not OpenSky

The original blog streams ADS-B aircraft positions from the OpenSky Network. Tested from swa-dev serverless on 2026-11-04:
- DNS resolves, but TCP connections to OpenSky (194.209.200.34:443) time out. Other public APIs (PyPI, GitHub, aviationweather.gov, weather.gov) work from the same compute, and OpenSky works from a laptop. The likely cause is OpenSky blocking cloud provider IP ranges. A workspace egress rule hasn't been ruled out.
- OpenSky data is licensed for non-commercial research use.

The METAR source teaches the same pattern (custom PySpark data source → streaming table) with a public government feed that works from serverless.
