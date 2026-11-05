# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 0 — Setup
# MAGIC
# MAGIC Creates your schema and a `raw` volume, then loads three public datasets into the volume:
# MAGIC
# MAGIC | Folder | What it is | Source |
# MAGIC |---|---|---|
# MAGIC | `bts/` | Southwest (WN) flight-level on-time performance, one CSV per month | US DOT Bureau of Transportation Statistics |
# MAGIC | `weather_history/` | Hourly METAR weather reports for 20 Southwest airports, local time | Iowa Environmental Mesonet (IEM) ASOS archive |
# MAGIC | `reference/` | Airport list with names, time zones, coordinates | Included in this notebook |
# MAGIC
# MAGIC If the instructor has already loaded a shared copy (`shared_schema`), the files are copied from there
# MAGIC instead of downloaded. Run time: about 1 minute from the shared copy, 3–5 minutes from the internet.
# MAGIC
# MAGIC Run on **serverless** compute.

# COMMAND ----------

dbutils.widgets.text("catalog", "temp_ai_training_2026", "Catalog")
dbutils.widgets.text("schema", "", "Schema (blank = your username)")
dbutils.widgets.text("shared_schema", "lab_shared", "Shared schema to copy from")
dbutils.widgets.text("months", "2026-06,2026-07,2026-08", "BTS months (YYYY-MM)")

import re

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
if not schema:
    user = spark.sql("SELECT current_user()").first()[0]
    schema = re.sub(r"[^a-z0-9]+", "_", user.split("@")[0].lower()).strip("_")
shared_schema = dbutils.widgets.get("shared_schema").strip()
months = [m.strip() for m in dbutils.widgets.get("months").split(",") if m.strip()]

raw_path = f"/Volumes/{catalog}/{schema}/raw"
shared_path = f"/Volumes/{catalog}/{shared_schema}/raw" if shared_schema and shared_schema != schema else None
print(f"Target: {catalog}.{schema}  ->  {raw_path}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}` COMMENT 'SWA ops Lakeflow lab'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.raw COMMENT 'Raw files for the SWA ops Lakeflow lab'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Airports
# MAGIC Twenty of Southwest's larger stations. Time zones are used to request weather in local time,
# MAGIC so weather lines up with BTS scheduled departure times (which are local).

# COMMAND ----------

AIRPORTS = [
    # code, icao, name, city, state, tz, lat, lon
    ("DAL", "KDAL", "Dallas Love Field", "Dallas", "TX", "America/Chicago", 32.8471, -96.8518),
    ("HOU", "KHOU", "William P. Hobby", "Houston", "TX", "America/Chicago", 29.6454, -95.2789),
    ("AUS", "KAUS", "Austin-Bergstrom", "Austin", "TX", "America/Chicago", 30.1945, -97.6699),
    ("SAT", "KSAT", "San Antonio International", "San Antonio", "TX", "America/Chicago", 29.5337, -98.4698),
    ("MDW", "KMDW", "Chicago Midway", "Chicago", "IL", "America/Chicago", 41.7860, -87.7524),
    ("STL", "KSTL", "St. Louis Lambert", "St. Louis", "MO", "America/Chicago", 38.7487, -90.3700),
    ("BNA", "KBNA", "Nashville International", "Nashville", "TN", "America/Chicago", 36.1245, -86.6782),
    ("DEN", "KDEN", "Denver International", "Denver", "CO", "America/Denver", 39.8561, -104.6737),
    ("PHX", "KPHX", "Phoenix Sky Harbor", "Phoenix", "AZ", "America/Phoenix", 33.4343, -112.0116),
    ("LAS", "KLAS", "Harry Reid International", "Las Vegas", "NV", "America/Los_Angeles", 36.0840, -115.1537),
    ("OAK", "KOAK", "Oakland International", "Oakland", "CA", "America/Los_Angeles", 37.7213, -122.2208),
    ("SJC", "KSJC", "San Jose Mineta", "San Jose", "CA", "America/Los_Angeles", 37.3626, -121.9291),
    ("SMF", "KSMF", "Sacramento International", "Sacramento", "CA", "America/Los_Angeles", 38.6954, -121.5908),
    ("SAN", "KSAN", "San Diego International", "San Diego", "CA", "America/Los_Angeles", 32.7336, -117.1897),
    ("LAX", "KLAX", "Los Angeles International", "Los Angeles", "CA", "America/Los_Angeles", 33.9416, -118.4085),
    ("BWI", "KBWI", "Baltimore/Washington", "Baltimore", "MD", "America/New_York", 39.1754, -76.6683),
    ("MCO", "KMCO", "Orlando International", "Orlando", "FL", "America/New_York", 28.4312, -81.3081),
    ("TPA", "KTPA", "Tampa International", "Tampa", "FL", "America/New_York", 27.9755, -82.5332),
    ("FLL", "KFLL", "Fort Lauderdale-Hollywood", "Fort Lauderdale", "FL", "America/New_York", 26.0742, -80.1506),
    ("ATL", "KATL", "Hartsfield-Jackson Atlanta", "Atlanta", "GA", "America/New_York", 33.6407, -84.4277),
]

# COMMAND ----------

import csv, io, os, shutil, time, urllib.request, zipfile
from datetime import date, timedelta

UA = {"User-Agent": "swa-ops-lakeflow-lab"}


def http_get(url, timeout=300, attempts=3):
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if i == attempts - 1:
                raise
            print(f"  retry after {type(e).__name__}: {e}")
            time.sleep(5 * (i + 1))


def has_files(path):
    return os.path.isdir(path) and any(f.endswith(".csv") for f in os.listdir(path))


def copy_from_shared(folder):
    src, dst = f"{shared_path}/{folder}", f"{raw_path}/{folder}"
    if not shared_path or not has_files(src):
        return False
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if not os.path.exists(f"{dst}/{f}"):
            shutil.copyfile(f"{src}/{f}", f"{dst}/{f}")
    print(f"{folder}: copied {len(os.listdir(dst))} files from {src}")
    return True

# COMMAND ----------

# Reference data
os.makedirs(f"{raw_path}/reference", exist_ok=True)
with open(f"{raw_path}/reference/airports.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["airport", "icao", "name", "city", "state", "tz", "latitude", "longitude"])
    w.writerows(AIRPORTS)
print("reference: wrote airports.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## BTS on-time performance (Southwest only)
# MAGIC Each monthly file from BTS covers every US carrier (~600k rows). We keep Southwest (`WN`) rows
# MAGIC and a readable subset of columns.

# COMMAND ----------

BTS_URL = "https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{y}_{m}.zip"
BTS_COLUMNS = [
    "FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Tail_Number",
    "Origin", "OriginCityName", "Dest", "DestCityName",
    "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15", "TaxiOut", "WheelsOff",
    "WheelsOn", "TaxiIn", "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15",
    "Cancelled", "CancellationCode", "Diverted", "CRSElapsedTime", "ActualElapsedTime", "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay",
]

if not copy_from_shared("bts"):
    os.makedirs(f"{raw_path}/bts", exist_ok=True)
    for ym in months:
        y, m = ym.split("-")
        out = f"{raw_path}/bts/wn_ontime_{y}_{int(m):02d}.csv"
        if os.path.exists(out):
            print(f"bts: {out} exists, skipping")
            continue
        print(f"bts: downloading {ym} ...")
        z = zipfile.ZipFile(io.BytesIO(http_get(BTS_URL.format(y=y, m=int(m)))))
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        kept = 0
        with z.open(name) as src, open(out + ".tmp", "w", newline="") as dst:
            reader = csv.DictReader(io.TextIOWrapper(src, encoding="latin-1"))
            writer = csv.writer(dst)
            writer.writerow(BTS_COLUMNS)
            for row in reader:
                if row["Reporting_Airline"] == "WN":
                    writer.writerow([row.get(c, "") for c in BTS_COLUMNS])
                    kept += 1
        os.replace(out + ".tmp", out)
        print(f"bts: {ym} -> {kept:,} Southwest flights")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Weather history (IEM ASOS archive)
# MAGIC Routine hourly METARs for the same months, requested per airport in that airport's local time zone.

# COMMAND ----------

IEM_URL = (
    "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={station}"
    "&data=tmpf&data=dwpf&data=drct&data=sknt&data=gust&data=vsby"
    "&data=skyc1&data=skyc2&data=skyc3&data=skyl1&data=skyl2&data=skyl3&data=wxcodes&data=metar"
    "&year1={y1}&month1={m1}&day1=1&year2={y2}&month2={m2}&day2=1"
    "&tz={tz}&format=onlycomma&latlon=no&elev=no&missing=M&trace=T&direct=no&report_type=3"
)

if not copy_from_shared("weather_history"):
    os.makedirs(f"{raw_path}/weather_history", exist_ok=True)
    first = date(int(months[0][:4]), int(months[0][5:7]), 1)
    last = date(int(months[-1][:4]), int(months[-1][5:7]), 1)
    end = (last + timedelta(days=32)).replace(day=1)       # first day of the month after the last month
    for code, *_, tz, _lat, _lon in AIRPORTS:
        out = f"{raw_path}/weather_history/{code}.csv"
        if os.path.exists(out):
            continue
        body = http_get(IEM_URL.format(station=code, tz=tz, y1=first.year, m1=first.month, y2=end.year, m2=end.month))
        with open(out + ".tmp", "wb") as f:
            f.write(body)
        os.replace(out + ".tmp", out)
        reports = body.count(b"\n") - 1
        print(f"weather_history: {code} -> {reports:,} reports")
        time.sleep(1)  # IEM asks for sequential, polite requests

# COMMAND ----------

for folder in ["bts", "weather_history", "reference"]:
    files = sorted(os.listdir(f"{raw_path}/{folder}"))
    size = sum(os.path.getsize(f"{raw_path}/{folder}/{f}") for f in files) / 1e6
    print(f"{folder:16s} {len(files):3d} files  {size:7.1f} MB")

print(f"\nDone. Use these values in Lab 1:\n  catalog  = {catalog}\n  schema   = {schema}\n  raw_path = {raw_path}")
