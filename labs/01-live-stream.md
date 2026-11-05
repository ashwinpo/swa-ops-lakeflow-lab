# Mission 1 — Stream live weather

**Time:** 25 min · **You'll use:** Lakeflow Pipelines Editor, Genie Code · **Docs:** [Genie Code for pipeline development](https://docs.databricks.com/aws/en/ldp/de-agent)

## The situation

The old dashboard's "current conditions" come from last night's extract. Ops wants weather that's minutes old, not hours. Weather reports (METARs) from US airports are published continuously by the NOAA Aviation Weather Center. Someone already wrote a **custom PySpark data source** that reads them: `my_pipeline/utilities/metar_source.py`. Your job is to turn it into a table that keeps itself up to date.

## Your goal

Create a pipeline with a **streaming table** of live weather reports. Run it twice and see that the second run adds only *new* reports.

## Key ideas

- A **pipeline** (Lakeflow Spark Declarative Pipelines) is a set of table definitions. You declare *what* each table is; the pipeline works out order, dependencies, checkpoints, and retries.
- A **streaming table** processes each new input record once and appends it. Good for data that arrives over time.
- A **custom data source** teaches Spark a new `format(...)`. This one is called `metar`.

## Steps (the what, not the how)

1. **Create a pipeline from your folder.** Sidebar → **Jobs & Pipelines** → **Create** (or **New**) → **ETL pipeline**. Choose the option to **add existing assets / source code**, and point it at your `my_pipeline` folder as the **root folder** and `my_pipeline/transformations` as the source folder. Set the default catalog `temp_ai_training_2026` and schema = yours. Name it `<you>_ops`.
2. **Read the data source before you use it.** Open `utilities/metar_source.py`. Read the docstring at the top. Then ask Genie Code to explain it to you. You should be able to answer: what are the options, and how does the stream avoid writing the same report twice?
3. **Declare the streaming table.** Ask Genie Code to create a streaming table from the `metar` data source in a new file under `transformations/`. Name and options are up to you.
4. **Run the pipeline.** Look at the graph, the table preview, and the row count.
5. **Run it again** a few minutes later. Compare the row counts.

### Prompt ingredients

A good Genie Code prompt for step 3 says: which file to create, that it's a **streaming table**, which **data source** to use (and where it's defined), which **options** you want, and what to **name** the table. Add a table comment. Ask for a data quality rule or two if you like.

## Done when

- The pipeline graph shows your streaming table, and its preview shows weather reports with `raw_text` like `METAR KDAL 051453Z 16003KT 10SM ...`.
- A second run adds only reports that are new since the first run.
- `check_progress`: **Mission 1** checks pass (the "every US station" check is a bonus).

## Stuck?

<details><summary>Hint 1 — where to look</summary>

Pipeline errors show on the red node in the graph and in the event log at the bottom of the editor. Click the node and read the first line of the error, not the stack trace.
</details>

<details><summary>Hint 2 — an approach</summary>

The registration line looks like `spark.dataSource.register(MetarDataSource)`. The streaming read looks like `spark.readStream.format("metar").option(...).load()`. In Python pipelines, a function decorated with `@dp.table` that returns a streaming DataFrame defines a streaming table (`from pyspark import pipelines as dp`). Or just give Genie Code the error: *"Fix the failure in this pipeline."*
</details>

<details><summary>Hint 3 — compare with the reference</summary>

`src/pipeline/transformations/01_bronze_metar_live.py` in your lab folder.
</details>

**Second run added 0 rows?** That can be correct: the 20 default airports report about once an hour. The data source can stream every US station instead. Find the option in the docstring.

## Reflect

- What did the pipeline do for you that you'd otherwise write yourself (checkpoints, retries, ordering)?
- The original Databricks blog this lab is based on did the same thing with live aircraft positions from OpenSky. What other live feeds at Southwest could you read this way?

## Stretch

- Set the data source's `mode` option to `synthetic` and run. What changes? How would you catch that in production? (Hint: expectations.)

Next: [Mission 2 — Bring in history and clean it](02-history.md)
