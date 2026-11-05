"""
Custom PySpark data source for live airport weather (METAR) observations.

Usage (in a pipeline file under transformations/):
    from utilities.metar_source import MetarDataSource
    spark.dataSource.register(MetarDataSource)

    spark.readStream.format("metar").option("stations", "KDAL,KMDW").load()   # streaming
    spark.read.format("metar").load()                                          # batch

Options:
    stations  Comma-separated ICAO station IDs, or "US" for every US reporting station
              (about 2,000; new reports arrive every few minutes). Defaults to 20 Southwest airports.
    mode      auto      -> try the aviationweather.gov bulk file, then its API, then synthetic data
              live      -> bulk file, then API; fail if both are down
              synthetic -> generated observations only (no network calls)
    timeout   HTTP timeout in seconds (default 30).

Data comes from the NOAA Aviation Weather Center (aviationweather.gov), a public
US government source. No API key is needed.
"""

import csv
import gzip
import sys
import io
import json
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from pyspark import cloudpickle
from pyspark.sql.datasource import (
    DataSource,
    DataSourceReader,
    InputPartition,
    SimpleDataSourceStreamReader,
)

DEFAULT_STATIONS = (
    "KDAL,KHOU,KAUS,KSAT,KMDW,KSTL,KBNA,KDEN,KPHX,KLAS,"
    "KOAK,KSJC,KSMF,KSAN,KLAX,KBWI,KMCO,KTPA,KFLL,KATL"
)

CACHE_URL = "https://aviationweather.gov/data/cache/metars.cache.csv.gz"
API_URL = "https://aviationweather.gov/api/data/metar?ids={ids}&format=json"
USER_AGENT = "swa-ops-lakeflow-lab"

SCHEMA = """
    station_id STRING,
    observation_time TIMESTAMP,
    latitude DOUBLE,
    longitude DOUBLE,
    temp_c DOUBLE,
    dewpoint_c DOUBLE,
    wind_dir_degrees INT,
    wind_speed_kt INT,
    wind_gust_kt INT,
    visibility_mi DOUBLE,
    altimeter_in_hg DOUBLE,
    wx_string STRING,
    ceiling_ft INT,
    flight_category STRING,
    raw_text STRING,
    source STRING,
    ingest_time TIMESTAMP
"""

CEILING_COVERS = {"BKN", "OVC", "OVX", "VV"}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _num(value, cast=float):
    if value is None:
        return None
    text = str(value).strip().rstrip("+")
    if text in ("", "VRB", "M"):
        return None
    try:
        return cast(float(text))
    except ValueError:
        return None


def _ceiling(layers):
    """Lowest broken/overcast layer, in feet above ground."""
    bases = [_num(base, int) for cover, base in layers if cover in CEILING_COVERS]
    bases = [b for b in bases if b is not None]
    return min(bases) if bases else None


def _flight_category(ceiling_ft, visibility_mi):
    """FAA flight category from ceiling and visibility."""
    if ceiling_ft is None and visibility_mi is None:
        return None
    c = ceiling_ft if ceiling_ft is not None else 99999
    v = visibility_mi if visibility_mi is not None else 99.0
    if c < 500 or v < 1:
        return "LIFR"
    if c < 1000 or v < 3:
        return "IFR"
    if c <= 3000 or v <= 5:
        return "MVFR"
    return "VFR"


US_PREFIXES = ("K", "PA", "PH", "TJ")   # contiguous US, Alaska, Hawaii, Puerto Rico


def _wanted(station, stations):
    if "US" in stations:
        return station.startswith(US_PREFIXES) and len(station) == 4
    return station in stations


def _http_get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _row(station, obs_time, lat, lon, temp, dewp, wdir, wspd, wgst, vis, altim,
         wx, ceiling, category, raw, source, now):
    return (station, obs_time, lat, lon, temp, dewp, wdir, wspd, wgst, vis, altim,
            wx, ceiling, category or _flight_category(ceiling, vis), raw, source, now)


# ---------------------------------------------------------------------------
# Fetchers: bulk file, JSON API, synthetic
# ---------------------------------------------------------------------------

def fetch_from_cache(stations, timeout):
    """Bulk file with the latest METAR for every reporting station (refreshed each minute)."""
    text = gzip.decompress(_http_get(CACHE_URL, timeout)).decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    col = {}
    for i, name in enumerate(header):
        col.setdefault(name, i)                       # first occurrence for scalar fields
    covers = [i for i, n in enumerate(header) if n == "sky_cover"]
    bases = [i for i, n in enumerate(header) if n == "cloud_base_ft_agl"]
    now = datetime.now(timezone.utc)
    rows = []
    for r in reader:
        if len(r) < len(header) or not _wanted(r[col["station_id"]], stations):
            continue
        layers = [(r[c], r[b]) for c, b in zip(covers, bases)]
        ceiling = _ceiling(layers)
        vis = _num(r[col["visibility_statute_mi"]])
        obs = datetime.strptime(r[col["observation_time"]], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        rows.append(_row(
            r[col["station_id"]], obs,
            _num(r[col["latitude"]]), _num(r[col["longitude"]]),
            _num(r[col["temp_c"]]), _num(r[col["dewpoint_c"]]),
            _num(r[col["wind_dir_degrees"]], int), _num(r[col["wind_speed_kt"]], int),
            _num(r[col["wind_gust_kt"]], int), vis, _num(r[col["altim_in_hg"]]),
            r[col["wx_string"]] or None, ceiling, r[col["flight_category"]] or None,
            r[col["raw_text"]], "aviationweather_cache", now,
        ))
    return rows


def fetch_from_api(stations, timeout):
    """JSON API. Used when the bulk file is unavailable."""
    if "US" in stations:
        stations = set(DEFAULT_STATIONS.split(","))
    data = json.loads(_http_get(API_URL.format(ids=",".join(sorted(stations))), timeout))
    now = datetime.now(timezone.utc)
    rows = []
    for d in data:
        layers = [(c.get("cover"), c.get("base")) for c in d.get("clouds") or []]
        ceiling = _ceiling(layers)
        vis = _num(d.get("visib"))
        altim_hpa = _num(d.get("altim"))
        rows.append(_row(
            d.get("icaoId"), datetime.fromtimestamp(d["obsTime"], tz=timezone.utc),
            _num(d.get("lat")), _num(d.get("lon")),
            _num(d.get("temp")), _num(d.get("dewp")),
            _num(d.get("wdir"), int), _num(d.get("wspd"), int), _num(d.get("wgst"), int),
            vis, round(altim_hpa * 0.02953, 2) if altim_hpa else None,
            d.get("wxString"), ceiling, d.get("fltCat"),
            d.get("rawOb"), "aviationweather_api", now,
        ))
    return rows


def synthetic_observations(stations):
    """Plausible hourly observations. Same station + hour always gives the same row."""
    now = datetime.now(timezone.utc)
    obs = now.replace(minute=53, second=0, microsecond=0)
    if obs > now:
        obs -= timedelta(hours=1)
    if "US" in stations:
        stations = set(DEFAULT_STATIONS.split(","))
    rows = []
    for station in sorted(stations):
        rnd = random.Random(f"{station}-{obs:%Y%m%d%H}")
        temp = round(rnd.uniform(-5, 35), 1)
        wspd = rnd.choice([0, 3, 5, 8, 10, 12, 15, 18, 22, 28])
        wgst = wspd + rnd.choice([8, 10, 12]) if wspd >= 15 and rnd.random() < 0.5 else None
        vis = rnd.choices([10.0, 6.0, 4.0, 2.0, 0.75], weights=[70, 12, 8, 6, 4])[0]
        ceiling = rnd.choices([None, 4500, 2500, 800, 300], weights=[55, 20, 13, 8, 4])[0]
        wx = rnd.choices([None, "-RA", "BR", "TSRA", "+RA"], weights=[75, 10, 8, 5, 2])[0]
        rows.append(_row(
            station, obs, None, None, temp, round(temp - rnd.uniform(1, 12), 1),
            rnd.randrange(0, 360, 10), wspd, wgst, vis, round(rnd.uniform(29.7, 30.3), 2),
            wx, ceiling, None, f"SYNTHETIC {station} {obs:%d%H%M}Z", "synthetic", now,
        ))
    return rows


def fetch_observations(stations, mode="auto", timeout=30):
    if mode == "synthetic":
        return synthetic_observations(stations)
    errors = []
    for fetch in (fetch_from_cache, fetch_from_api):
        try:
            rows = fetch(stations, timeout)
            if rows:
                return rows
            errors.append(f"{fetch.__name__}: no rows")
        except Exception as e:  # network errors, upstream 5xx, parse errors
            errors.append(f"{fetch.__name__}: {type(e).__name__}: {e}")
    if mode == "live":
        raise RuntimeError("Live METAR sources unavailable: " + "; ".join(errors))
    return synthetic_observations(stations)


def _parse_stations(options):
    raw = options.get("stations") or DEFAULT_STATIONS
    return {s.strip().upper() for s in raw.split(",") if s.strip()}


# ---------------------------------------------------------------------------
# Spark data source
# ---------------------------------------------------------------------------

class MetarDataSource(DataSource):
    """Registers as format("metar")."""

    @classmethod
    def name(cls):
        return "metar"

    def schema(self):
        return SCHEMA

    def reader(self, schema):
        return MetarBatchReader(self.options)

    def simpleStreamReader(self, schema):
        return MetarStreamReader(self.options)


class MetarBatchReader(DataSourceReader):
    def __init__(self, options):
        self.stations = _parse_stations(options)
        self.mode = options.get("mode", "auto")
        self.timeout = int(options.get("timeout", 30))

    def partitions(self):
        return [InputPartition(0)]

    def read(self, partition):
        yield from fetch_observations(self.stations, self.mode, self.timeout)


class MetarStreamReader(SimpleDataSourceStreamReader):
    """
    Each micro-batch polls the source once. The offset holds the last observation
    time seen per station, so a station's report is emitted once even though the
    source keeps returning it until the next report replaces it.
    """

    def __init__(self, options):
        self.stations = _parse_stations(options)
        self.mode = options.get("mode", "auto")
        self.timeout = int(options.get("timeout", 30))

    def initialOffset(self):
        return {}

    def _new_rows(self, start, end=None):
        rows = []
        for row in fetch_observations(self.stations, self.mode, self.timeout):
            station, ts = row[0], row[1].isoformat()
            if ts <= start.get(station, ""):
                continue
            if end is not None and ts > end.get(station, ""):
                continue
            rows.append(row)
        return rows

    def read(self, start):
        rows = self._new_rows(start)
        end = dict(start)
        for row in rows:
            end[row[0]] = max(end.get(row[0], ""), row[1].isoformat())
        return iter(rows), end

    def readBetweenOffsets(self, start, end):
        # Replays after a failure. The source only keeps the latest report per station,
        # so rows that have since been replaced cannot be re-fetched.
        return iter(self._new_rows(start, end))

    def commit(self, end):
        pass


# Spark runs data sources in a separate Python worker that can't import files from the
# pipeline folder. Pickling this module by value ships its code to that worker, so the
# source works from utilities/ without being installed as a package.
cloudpickle.register_pickle_by_value(sys.modules[__name__])
