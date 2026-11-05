# Mission 6 — Decide where Genie lives

**Time:** 20 min · **You'll use:** AI/BI dashboards, Genie · **Docs:** [Genie on dashboards](https://docs.databricks.com/aws/en/dashboards/genie-spaces)

## The situation

The old dashboard's last problem: every follow-up question became an email. Genie lets people ask in plain English and get an answer with the SQL behind it. But there's more than one place to put it, and teams at Southwest will face this choice on every dashboard they migrate.

## The options

| | **Genie on the dashboard** | **Standalone Genie agent** | **Genie inside an app** |
|---|---|---|---|
| How | Publish with **Enable Genie** on. A companion agent is created from the dashboard's datasets, or you link an existing agent. | Sidebar → **Genie** → **New**. Pick tables, write instructions, add example questions. | An app calls a Genie agent (Mission 7). |
| Users ask about | What's on this dashboard | A whole subject area, across many tables | Whatever the app is for, inside its workflow |
| You can tune | Little. The companion agent is rebuilt from the dashboard when you republish; its instructions can't be edited. | Instructions, example SQL, trusted answers, table and column descriptions | Same as the agent it uses |
| Good when | Viewers want "why is this number high?" next to the chart | Analysts and leaders explore beyond one dashboard | The question is one step in a task |

## Your goal

1. Pick **one** option for Ops, implement it, and ask it at least **five** questions.
2. Write two or three sentences in the dashboard's text box (or a notebook cell) explaining **why** you picked it for this audience.

## Questions to try

1. Which airports are reporting IFR or LIFR right now, and how did Southwest do historically in those conditions there?
2. How much higher is the delay rate in thunderstorms than in clear weather, by airport?
3. What were the five worst days at Chicago Midway, and what was the weather?
4. Which hour of the day is worst for delays at Denver?
5. Is IFR without thunderstorms really better than VFR? Why might that be?

For each, click **Show code** at least once. Is the SQL doing what you meant?

## If you build a standalone agent

Add instructions with the definitions people will assume: what "delayed" means (15+ minutes), what "bad weather" means (IFR or LIFR), that history is June–August 2026, and that live conditions are current but not joined to current flights. When an answer is right, save it as a trusted answer. When it's wrong, fix the SQL and save the correct version.

## Done when

- Genie answers questions 1–3 correctly on your data.
- Your "why this option" note exists.
- `check_progress`: **Mission 6** passes.

## Reflect

- Your neighbor picked differently. Compare reasons. Which would you choose for station leaders on their phones? For the Ops analytics team?

Next: [Mission 7 — Build an app with Genie App Builder](07-app.md)
