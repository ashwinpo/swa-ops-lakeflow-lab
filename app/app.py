"""
SWA Ops Board — live airport weather next to historical Southwest delay rates.

Reads the gold tables built by the lab pipeline. Queries run as the signed-in user
(Databricks Apps user authorization, scope `sql`), so each person sees the tables
they have access to. Falls back to the app's service principal when no user token
is present (for example, when running locally).
"""

import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

st.set_page_config(page_title="SWA Ops Board", layout="wide")

cfg = Config()
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]
CATALOG = os.environ.get("LAB_CATALOG", "temp_ai_training_2026")

CATEGORY_ORDER = ["VFR", "MVFR", "IFR", "LIFR", "UNKNOWN"]
CATEGORY_COLORS = {"VFR": "#2e7d32", "MVFR": "#1565c0", "IFR": "#c62828", "LIFR": "#8e24aa", "UNKNOWN": "#9e9e9e"}


def user_token():
    return st.context.headers.get("X-Forwarded-Access-Token")


def connect():
    token = user_token()
    if token:
        return sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}", access_token=token)
    return sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
                       credentials_provider=lambda: cfg.authenticate)


@st.cache_data(ttl=60, show_spinner=False)
def run_query(query, _token_key):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()


def query(q):
    # Cache per user so one person's results are never shown to another.
    return run_query(q, user_token() or "app")


def default_schema():
    if os.environ.get("LAB_SCHEMA"):
        return os.environ["LAB_SCHEMA"]
    user = query("SELECT current_user() AS u")["u"][0]
    return re.sub(r"[^a-z0-9]+", "_", user.split("@")[0].lower()).strip("_")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("SWA Ops Board")
schema = st.sidebar.text_input("Schema", value=default_schema(), help="Your lab schema in " + CATALOG)
fq = f"`{CATALOG}`.`{schema}`"
if st.sidebar.button("Refresh data"):
    run_query.clear()
st.sidebar.caption("Weather: NOAA Aviation Weather Center (live) and Iowa Environmental Mesonet (history). "
                   "Flights: US DOT BTS on-time performance, Southwest (WN). Public data only.")

try:
    live = query(f"SELECT * FROM {fq}.gold_live_delay_risk ORDER BY delay_pts_vs_clear DESC NULLS LAST")
except Exception as e:
    st.error(f"Could not read {fq}.gold_live_delay_risk. Has your pipeline run?\n\n{e}")
    st.stop()

tab_live, tab_hist, tab_daily = st.tabs(["Live conditions", "Delay by weather", "Daily performance"])

# ---------------------------------------------------------------------------
# Live conditions
# ---------------------------------------------------------------------------

with tab_live:
    latest = live["observation_time"].max()
    st.subheader("Current conditions and historical delay risk")
    st.caption(f"Latest observation: {latest} UTC · source: {', '.join(sorted(live['source'].dropna().unique()))}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Airports reporting", int(live["observation_time"].notna().sum()))
    c2.metric("IFR or LIFR now", int(live["flight_category"].isin(["IFR", "LIFR"]).sum()))
    c3.metric("Thunderstorms now", int(live["thunderstorm"].fillna(False).sum()))
    c4.metric("High wind now", int(live["high_wind"].fillna(False).sum()))

    left, right = st.columns([3, 2])
    with left:
        geo = live.dropna(subset=["latitude"]).assign(
            marker_size=lambda d: d["hist_pct_dep_delayed_15"].fillna(5).clip(lower=5))
        fig = px.scatter_geo(
            geo, lat="latitude", lon="longitude", scope="usa",
            color="flight_category", color_discrete_map=CATEGORY_COLORS,
            category_orders={"flight_category": CATEGORY_ORDER},
            size="marker_size", hover_name="airport",
            hover_data={"name": True, "raw_text": True, "hist_pct_dep_delayed_15": True,
                        "marker_size": False, "latitude": False, "longitude": False},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=420, legend_title_text="Flight category")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("**Historical % of departures delayed 15+ min in these conditions**")
        st.dataframe(
            live[["airport", "flight_category", "hist_pct_dep_delayed_15", "clear_pct_dep_delayed_15",
                  "delay_pts_vs_clear", "hist_departures_same_conditions"]],
            hide_index=True, use_container_width=True, height=420,
            column_config={
                "hist_pct_dep_delayed_15": st.column_config.NumberColumn("Same conditions %", format="%.1f"),
                "clear_pct_dep_delayed_15": st.column_config.NumberColumn("Clear weather %", format="%.1f"),
                "delay_pts_vs_clear": st.column_config.NumberColumn("Difference (pts)", format="%+.1f"),
                "hist_departures_same_conditions": st.column_config.NumberColumn("Sample size"),
            },
        )
    with st.expander("Raw METAR reports"):
        st.dataframe(live[["airport", "observation_time", "raw_text", "source"]], hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Delay by weather
# ---------------------------------------------------------------------------

with tab_hist:
    hist = query(f"SELECT * FROM {fq}.gold_delay_by_weather")
    airports = sorted(hist["airport"].unique())
    c1, c2 = st.columns([3, 1])
    pick = c1.multiselect("Airports", airports, default=[a for a in ["DAL", "MDW", "BWI", "DEN"] if a in airports])
    min_deps = c2.number_input("Minimum departures", min_value=1, value=30, step=10,
                               help="Hide condition groups with too few flights to compare")
    view = hist[hist["airport"].isin(pick)] if pick else hist
    view = view[view["departures"] >= min_deps]
    view = view.assign(conditions=view["flight_category"] + view["thunderstorm"].map({True: " + TS", False: ""}))
    conditions_order = [c + ts for c in CATEGORY_ORDER for ts in ("", " + TS")]
    fig = px.bar(view, x="conditions", y="pct_dep_delayed_15", color="airport", barmode="group",
                 category_orders={"conditions": conditions_order},
                 hover_data=["departures", "avg_dep_delay_min", "pct_cancelled"],
                 labels={"pct_dep_delayed_15": "% departures delayed 15+ min", "conditions": "Weather at departure"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(view.drop(columns=["conditions"]), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Daily performance
# ---------------------------------------------------------------------------

with tab_daily:
    daily = query(f"SELECT * FROM {fq}.gold_airport_daily ORDER BY flight_date")
    pick = st.selectbox("Airport", sorted(daily["airport"].unique()), index=0)
    d = daily[daily["airport"] == pick]
    fig = px.line(d, x="flight_date", y="pct_dep_delayed_15", markers=True,
                  hover_data=["departures", "departures_in_ifr", "departures_in_thunderstorms"],
                  labels={"pct_dep_delayed_15": "% departures delayed 15+ min", "flight_date": ""})
    st.plotly_chart(fig, use_container_width=True)
    worst = d.sort_values("pct_dep_delayed_15", ascending=False).head(5)
    st.markdown("**Worst five days**")
    st.dataframe(worst, hide_index=True, use_container_width=True)
