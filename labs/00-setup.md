# Lab 0 — Setup

**Goal:** get a copy of the lab files in your workspace folder and load the raw data into your own schema.

## 1. Copy the lab folder

Your instructor has published the lab to `/Workspace/Shared/swa-ops-lakeflow-lab`.

1. In the left sidebar, click **Workspace** and open `Shared` → `swa-ops-lakeflow-lab`.
2. Click the kebab menu (⋮) next to the folder name → **Clone**.
3. Set the destination to your home folder (`/Workspace/Users/<you>`) and click **Clone**.

Work from your copy from here on. Edits to your copy don't affect anyone else.

> If your team uses Git folders, you can instead create a Git folder from the repo URL your instructor shares.

## 2. Run the setup notebook

1. Open `src/setup/00_setup` in your copy.
2. In the compute selector at the top right, choose **Serverless**.
3. Leave the widgets at their defaults:
   - `catalog` = `temp_ai_training_2026`
   - `schema` = blank (your username is used, e.g. `jane_doe`)
   - `shared_schema` = `lab_shared`
4. Click **Run all**.

The notebook:
- creates the schema `temp_ai_training_2026.<you>` and a volume named `raw`
- copies three folders into `/Volumes/temp_ai_training_2026/<you>/raw/` from the instructor's shared copy, or downloads them if no shared copy exists:
  - `bts/` — Southwest flights, one CSV per month
  - `weather_history/` — hourly weather per airport
  - `reference/airports.csv` — the 20 airports in the lab

The last cell prints your `catalog`, `schema`, and `raw_path`. **Write down `raw_path`**; you need it in Lab 1.

## 3. Look at the files

In the left sidebar, click **Catalog** → `temp_ai_training_2026` → your schema → **Volumes** → `raw`. Open one BTS file and one weather file and look at the first rows.

Things to notice:
- BTS times like `CRSDepTime` are local `hhmm` strings (`0545`), and cancellations have no delay values.
- Weather files use `M` for missing values. Cloud layers are in `skyc1..3` (cover) and `skyl1..3` (height in feet).

These are the problems the silver layer solves in Lab 1.

## Checkpoint

- [ ] `temp_ai_training_2026.<you>` exists and has a `raw` volume
- [ ] The volume has `bts/` (3 files), `weather_history/` (20 files), `reference/` (1 file)

Next: [Lab 1 — Build the pipeline](01-pipeline.md)
