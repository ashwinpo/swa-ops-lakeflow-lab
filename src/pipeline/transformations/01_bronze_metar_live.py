# Live airport weather, streamed through a custom PySpark data source.
# The source code is in ../utilities/metar_source.py.

from pyspark import pipelines as dp

from utilities.metar_source import DEFAULT_STATIONS, MetarDataSource

spark.dataSource.register(MetarDataSource)

STATIONS = spark.conf.get("lab.stations", DEFAULT_STATIONS)
MODE = spark.conf.get("lab.metar_mode", "auto")   # auto | live | synthetic


@dp.table(
    name="bronze_metar_live",
    comment="Live METAR observations for Southwest airports (aviationweather.gov). One row per new report.",
)
@dp.expect_or_drop("has_station", "station_id IS NOT NULL")
@dp.expect_or_drop("has_observation_time", "observation_time IS NOT NULL")
@dp.expect("live_not_synthetic", "source <> 'synthetic'")
def bronze_metar_live():
    return (
        spark.readStream.format("metar")
        .option("stations", STATIONS)
        .option("mode", MODE)
        .load()
    )
