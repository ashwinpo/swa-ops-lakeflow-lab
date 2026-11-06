# Wrap-up

**Time:** 10 min

## Show and tell

Pair up. In two minutes each, show your dashboard (and app, if you built one), and answer:
1. How fresh is the data on your dashboard, and what decides that?
2. Is dashboard Genie enough for Ops, or would you add a standalone agent? Why?
3. One prompt that worked well, and one that didn't.

## What you built, and the pattern behind it

| You built | The pattern | Where you'd use it at Southwest |
|---|---|---|
| Streaming table on a live feed | Custom data source → streaming table | Any API or feed without a connector |
| Auto Loader tables on files | Files land in a volume → processed once | Vendor drops, exports, logs |
| Cleaned, joined, summarized tables | Materialized views on streaming tables | Any reporting layer |
| Expectations | Data quality rules in the pipeline | Trust before you publish |
| Scheduled pipeline + dashboard schedule | Freshness is a choice | Replacing nightly extracts |
| AI/BI dashboard built with Genie Code | Dashboard straight on governed tables | Tableau migrations |
| Genie on the dashboard or standalone | Q&A next to the data | Fewer "can you pull..." emails |
| App with Genie App Builder | Small tools on governed data | Spreadsheets and group chats that run a process |

## Clean up

Please do this before you leave:
1. **Jobs & Pipelines** → your pipeline's schedule job → **Pause** (or delete it). If you used continuous mode, stop the pipeline.
2. **Dashboards** → your dashboard → remove the schedule.
3. If you built an app: app switcher → **Databricks Apps** → your app → **Stop**.
4. Your schema is in a temporary catalog that will be deleted after the training. To delete it yourself now: `DROP SCHEMA temp_ai_training_2026.<you> CASCADE;`

## Keep going

- Add a new month of BTS data to `raw/bts/` (change `months` in `00_setup` and rerun). Watch only the new file get processed.
- Ask Genie Code: *"Is my delay summary refreshed incrementally or fully recomputed? Why?"*
- Write your own `AGENTS.md` for a dataset your team owns.
