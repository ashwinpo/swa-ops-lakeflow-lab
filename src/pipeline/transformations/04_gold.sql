-- Analytics tables for Genie and the app.

CREATE OR REFRESH MATERIALIZED VIEW gold_flights_weather
COMMENT "Each Southwest departure joined to the weather report in effect at its origin in the scheduled departure hour."
AS SELECT
  f.*,
  w.flight_category,
  w.thunderstorm,
  w.high_wind,
  w.visibility_mi,
  w.ceiling_ft,
  w.wind_kt,
  w.gust_kt,
  w.wx_codes
FROM silver_flights f
LEFT JOIN silver_weather_hourly w
  ON f.origin = w.airport AND f.flight_date = w.obs_date AND f.sched_dep_hour = w.obs_hour
WHERE f.origin IN (SELECT airport FROM dim_airports);

CREATE OR REFRESH MATERIALIZED VIEW gold_delay_by_weather
COMMENT "Departure delay and cancellation rates by origin airport and weather condition at departure time."
AS SELECT
  origin                                                        AS airport,
  flight_category,
  thunderstorm,
  COUNT(*)                                                      AS departures,
  ROUND(AVG(dep_delay_min), 1)                                  AS avg_dep_delay_min,
  ROUND(100 * AVG(CAST(dep_delayed_15 AS INT)), 1)              AS pct_dep_delayed_15,
  ROUND(100 * AVG(CAST(cancelled AS INT)), 2)                   AS pct_cancelled,
  ROUND(AVG(taxi_out_min), 1)                                   AS avg_taxi_out_min
FROM gold_flights_weather
WHERE flight_category IS NOT NULL
GROUP BY origin, flight_category, thunderstorm;

CREATE OR REFRESH MATERIALIZED VIEW gold_airport_daily
COMMENT "Daily Southwest departure performance and weather summary per airport."
AS SELECT
  origin                                                        AS airport,
  flight_date,
  COUNT(*)                                                      AS departures,
  ROUND(100 * AVG(CAST(dep_delayed_15 AS INT)), 1)              AS pct_dep_delayed_15,
  ROUND(100 * AVG(CAST(cancelled AS INT)), 2)                   AS pct_cancelled,
  ROUND(AVG(dep_delay_min), 1)                                  AS avg_dep_delay_min,
  SUM(CAST(weather_delay_min > 0 AS INT))                       AS flights_with_weather_delay,
  COUNT_IF(flight_category IN ('IFR', 'LIFR'))                  AS departures_in_ifr,
  COUNT_IF(thunderstorm)                                        AS departures_in_thunderstorms
FROM gold_flights_weather
GROUP BY origin, flight_date;

CREATE OR REFRESH MATERIALIZED VIEW gold_live_delay_risk
COMMENT "Current conditions at each airport next to the historical Southwest delay rate for the same conditions and for clear weather."
AS
WITH hist AS (
  SELECT airport, flight_category, thunderstorm, departures, pct_dep_delayed_15, avg_dep_delay_min, pct_cancelled
  FROM gold_delay_by_weather
),
baseline AS (
  SELECT airport, pct_dep_delayed_15 AS clear_pct_dep_delayed_15
  FROM hist WHERE flight_category = 'VFR' AND NOT thunderstorm
)
SELECT
  a.airport, a.name, a.city, a.state,
  CAST(a.latitude AS DOUBLE)  AS latitude,
  CAST(a.longitude AS DOUBLE) AS longitude,
  l.observation_time, l.flight_category, l.thunderstorm, l.high_wind,
  l.visibility_mi, l.ceiling_ft, l.wind_speed_kt, l.wind_gust_kt, l.wx_string, l.raw_text, l.source,
  h.departures              AS hist_departures_same_conditions,
  h.pct_dep_delayed_15      AS hist_pct_dep_delayed_15,
  h.avg_dep_delay_min       AS hist_avg_dep_delay_min,
  h.pct_cancelled           AS hist_pct_cancelled,
  b.clear_pct_dep_delayed_15,
  ROUND(h.pct_dep_delayed_15 - b.clear_pct_dep_delayed_15, 1) AS delay_pts_vs_clear
FROM dim_airports a
LEFT JOIN silver_metar_latest l ON a.icao = l.station_id
LEFT JOIN hist h ON h.airport = l.airport AND h.flight_category = l.flight_category AND h.thunderstorm = l.thunderstorm
LEFT JOIN baseline b ON b.airport = a.airport;
