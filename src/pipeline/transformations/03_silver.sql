-- Cleaned, typed data.

CREATE OR REFRESH STREAMING TABLE silver_flights (
  CONSTRAINT valid_flight_date EXPECT (flight_date IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_origin EXPECT (origin IS NOT NULL AND dest IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_sched_hour EXPECT (sched_dep_hour BETWEEN 0 AND 23) ON VIOLATION DROP ROW,
  CONSTRAINT delay_reported EXPECT (cancelled OR diverted OR dep_delay_min IS NOT NULL)
)
COMMENT "One row per scheduled Southwest flight. Times are local to the origin airport."
AS SELECT
  CAST(FlightDate AS DATE)                              AS flight_date,
  Reporting_Airline                                     AS carrier,
  CAST(Flight_Number_Reporting_Airline AS INT)          AS flight_number,
  Tail_Number                                           AS tail_number,
  Origin                                                AS origin,
  Dest                                                  AS dest,
  CONCAT(Origin, '-', Dest)                             AS route,
  CAST(CRSDepTime AS INT)                               AS sched_dep_hhmm,
  CAST(CAST(CRSDepTime AS INT) DIV 100 AS INT)          AS sched_dep_hour,
  CAST(DepDelay AS DOUBLE)                              AS dep_delay_min,
  CAST(DepDel15 AS DOUBLE) = 1                          AS dep_delayed_15,
  CAST(ArrDelay AS DOUBLE)                              AS arr_delay_min,
  CAST(ArrDel15 AS DOUBLE) = 1                          AS arr_delayed_15,
  CAST(Cancelled AS DOUBLE) = 1                         AS cancelled,
  CASE CancellationCode WHEN 'A' THEN 'carrier' WHEN 'B' THEN 'weather'
                        WHEN 'C' THEN 'nas' WHEN 'D' THEN 'security' END AS cancellation_reason,
  CAST(Diverted AS DOUBLE) = 1                          AS diverted,
  CAST(TaxiOut AS DOUBLE)                               AS taxi_out_min,
  CAST(TaxiIn AS DOUBLE)                                AS taxi_in_min,
  CAST(Distance AS DOUBLE)                              AS distance_mi,
  CAST(CarrierDelay AS DOUBLE)                          AS carrier_delay_min,
  CAST(WeatherDelay AS DOUBLE)                          AS weather_delay_min,
  CAST(NASDelay AS DOUBLE)                              AS nas_delay_min,
  CAST(LateAircraftDelay AS DOUBLE)                     AS late_aircraft_delay_min
FROM STREAM(bronze_bts_flights);

CREATE OR REFRESH MATERIALIZED VIEW silver_weather_hourly
COMMENT "One weather report per airport per local hour, with ceiling and FAA flight category (VFR, MVFR, IFR, LIFR). obs_hour is the hour the report applies to: a 14:53 report covers departures from 15:00 to 15:59."
AS
WITH typed AS (
  SELECT
    station                                                   AS airport,
    to_timestamp(valid, 'yyyy-MM-dd HH:mm')                   AS obs_time_local,
    try_cast(tmpf AS DOUBLE)                                  AS temp_f,
    try_cast(sknt AS DOUBLE)                                  AS wind_kt,
    try_cast(gust AS DOUBLE)                                  AS gust_kt,
    try_cast(vsby AS DOUBLE)                                  AS visibility_mi,
    NULLIF(wxcodes, 'M')                                      AS wx_codes,
    least(
      CASE WHEN skyc1 IN ('BKN', 'OVC', 'VV') THEN try_cast(skyl1 AS INT) END,
      CASE WHEN skyc2 IN ('BKN', 'OVC', 'VV') THEN try_cast(skyl2 AS INT) END,
      CASE WHEN skyc3 IN ('BKN', 'OVC', 'VV') THEN try_cast(skyl3 AS INT) END
    )                                                         AS ceiling_ft,
    metar
  FROM bronze_weather_history
),
hourly AS (
  SELECT *,
    obs_time_local + INTERVAL 7 MINUTES AS applies_to,
    ROW_NUMBER() OVER (
      PARTITION BY airport, date_trunc('HOUR', obs_time_local + INTERVAL 7 MINUTES)
      ORDER BY obs_time_local DESC
    ) AS rn
  FROM typed
  WHERE obs_time_local IS NOT NULL
)
SELECT
  airport,
  CAST(applies_to AS DATE)  AS obs_date,
  hour(applies_to)          AS obs_hour,
  obs_time_local,
  temp_f, wind_kt, gust_kt, visibility_mi, ceiling_ft, wx_codes,
  CASE
    WHEN ceiling_ft IS NULL AND visibility_mi IS NULL THEN 'UNKNOWN'
    WHEN ceiling_ft < 500  OR visibility_mi < 1 THEN 'LIFR'
    WHEN ceiling_ft < 1000 OR visibility_mi < 3 THEN 'IFR'
    WHEN ceiling_ft <= 3000 OR visibility_mi <= 5 THEN 'MVFR'
    ELSE 'VFR'
  END                                         AS flight_category,
  coalesce(wx_codes RLIKE 'TS', false)        AS thunderstorm,
  coalesce(greatest(wind_kt, gust_kt) >= 25, false) AS high_wind,
  metar
FROM hourly
WHERE rn = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_metar_latest
COMMENT "Most recent live METAR per airport."
AS SELECT
  -- Only contiguous-US K stations map to a 3-letter code (KDAL -> DAL). With stations=US the feed also
  -- has Alaska/Hawaii codes like PATL, which would collide with ATL if we just dropped the first letter.
  CASE WHEN station_id LIKE 'K___' THEN substring(station_id, 2) END AS airport,
  station_id,
  observation_time,
  temp_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, visibility_mi, ceiling_ft,
  wx_string, flight_category,
  coalesce(wx_string RLIKE 'TS', false)                                AS thunderstorm,
  coalesce(greatest(wind_speed_kt, wind_gust_kt) >= 25, false)         AS high_wind,
  raw_text, source, ingest_time
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY observation_time DESC, ingest_time DESC) AS rn
  FROM bronze_metar_live
)
WHERE rn = 1;
