# The staging watermark gap

**Found:** 2026-08-19, while verifying the two-lane split.
**Status:** open, untouched. Deliberately not fixed in the lane-split window.
**Severity:** high — this is not a historical backfill gap, it is happening every month.

---

## What is wrong

Roughly **28% of eligible member posts and comments never reach the helpdesk**. They exist in
`dataform.core_posts` / `core_comments`, they pass every business filter, and they simply never
get staged. Coaches cannot see them, so they are never answered.

| month | eligible | staged | missing |
|---|---|---|---|
| 2026-02 | 1,474 | 12 | **99.2%** |
| 2026-03 | 1,708 | 780 | 54.3% |
| 2026-04 | 1,749 | 1,245 | 28.8% |
| 2026-05 | 1,584 | 1,141 | 28.0% |
| 2026-06 | 1,489 | 882 | 40.8% |
| 2026-07 | 1,541 | 1,105 | 28.3% |
| 2026-08 | 497 | 458 | 7.8% |

August looks better only because the gap is created *retroactively* — see the mechanism below.
Those rows have not been overtaken yet. Expect August to settle around 28% too.

Totals as of 2026-08-19:

| model | eligible | staged | missing |
|---|---|---|---|
| `stg_grant_member_comments` | 5,737 | 2,874 | 2,885 |
| `stg_grant_posts` | 3,728 | 2,773 | 974 |
| `stg_grant_articles` | 527 | 376 | 151 |
| **total** | | | **4,010** |

## Why it happens

All three models are `type: "incremental"` and share this predicate:

```sql
${ when(incremental(), `AND created_at > (SELECT MAX(created_at) FROM ${self()})`) }
```

That is a **high-water mark on `created_at`**, a business timestamp, used as if it were an
ingestion timestamp. The two are not the same thing. `core_*` is itself synced from Mighty
Networks, and rows land there out of order — sync lag, backfills, and edits that flip
`comment_status` to `active` long after the comment was written.

The failure is one-way and permanent. Once the watermark advances past a row's `created_at`,
that row can never satisfy `created_at > MAX(created_at)` again. It is not retried, and nothing
reports it as skipped. February is 99.2% missing because the pipeline's first run set the
watermark to the newest row it saw and abandoned everything older in one step.

## Why you must not just run `--full-refresh`

It is the obvious fix and it is a trap. Three reasons:

1. **It floods the queue.** ~4,010 rows appear at once. At the classifier's current acceptance
   rate (7,191 classified, 4,656 questions = **64.7%**) that is roughly **2,600 new open
   tickets**, most of them months old, landing on the coaches without warning.
2. **It costs real money.** Every recovered row goes through `grant_question_classifier`
   (`gemini-2.5-flash` via BigQuery ML). 4,010 unbudgeted classifications.
3. **It hides behind unrelated work.** This was nearly shipped inside the two-lane deploy,
   where the 4,000 extra rows would have been indistinguishable from the lane change. Whatever
   fixes this should be the only thing moving at the time.

## Suggested approach

**Step 1 — stop the bleeding.** Replace the watermark with a bounded lookback. All three models
already declare `uniqueKey: ["content_id"]`, so Dataform emits a `MERGE` on incremental runs and
reprocessing an overlapping window cannot create duplicates:

```sql
${ when(incremental(), `AND created_at > TIMESTAMP_SUB(
     (SELECT MAX(created_at) FROM ${self()}), INTERVAL 30 DAY)`) }
```

Pick the interval from how late data actually arrives — measure it, do not guess. If `core_*`
exposes a true ingestion timestamp, keying on that instead is strictly better than any lookback.
Verify the `MERGE` assumption on one model before trusting it on all three.

**Step 2 — decide what to do with the 4,010 already lost.** This is a product call for Lise and
the team, not a technical one. Options, cheapest first:

- **Leave them.** The gap stays, but nothing new is missed.
- **Backfill archived.** Recover them, but land them terminal so they are searchable without
  entering the queue. The two-lane work added exactly this mechanism: `ticket_status = 'archived'`
  with a date cutoff in `grant_tickets.sqlx`. Reusing it here is a small change and the safest
  way to get the history back.
- **Backfill live.** ~2,600 new open tickets. Only if the team actually wants to work them.

**Recommendation: step 1 now, then backfill archived.** It restores the record, costs one
classifier pass, and puts nothing on the coaches' plate.

## How to verify

Reproduce the numbers before and after — this query needs no rebuild and touches no tables:

```sql
WITH eligible AS (
  SELECT CONCAT("comment_", CAST(comment_id AS STRING)) content_id, created_at
  FROM `bigtribebuilders.dataform.core_comments`
  WHERE client_id="lesko_4022250" AND comment_status="active" AND targetable_type="Post"
    AND author_id NOT IN (SELECT member_id FROM `bigtribebuilders.grant_helpdesk.stg_grant_team_members`)
  UNION ALL
  SELECT CONCAT("post_", CAST(post_id AS STRING)), created_at
  FROM `bigtribebuilders.dataform.core_posts`
  WHERE client_id="lesko_4022250" AND post_status="active"
    AND creator_id NOT IN (SELECT member_id FROM `bigtribebuilders.grant_helpdesk.stg_grant_team_members`)
),
staged AS (
  SELECT content_id FROM `bigtribebuilders.grant_helpdesk.stg_grant_member_comments`
  UNION ALL SELECT content_id FROM `bigtribebuilders.grant_helpdesk.stg_grant_posts`
)
SELECT FORMAT_DATE("%Y-%m", DATE(e.created_at)) month,
       COUNT(*) eligible, COUNTIF(s.content_id IS NOT NULL) staged,
       ROUND(100*COUNTIF(s.content_id IS NULL)/COUNT(*),1) pct_missing
FROM eligible e LEFT JOIN staged s USING(content_id)
WHERE DATE(e.created_at) >= "2026-02-01"
GROUP BY 1 ORDER BY 1;
```

Then leave it running as an assertion, so this cannot silently return. A pipeline that drops a
quarter of its input and says nothing is the actual bug; the predicate is only how it happens.

## Traps in this repo, learned the hard way

Read these before touching anything. Each one cost time on 2026-08-19.

**The Dataform schedule runs pinned snapshots, not `main`.** A release config named `main`
compiles the branch **hourly** (`0 * * * *`); a workflow config `grant-helpdesk-5min` executes
the latest compiled release **every 30 minutes** (`*/30 * * * *`). So for up to an hour after you
push, scheduled runs still rebuild your tables from the *old* code. This silently reverted a
schema change twice in one afternoon. Freeze it for the duration of a migration:

```
PATCH .../workflowConfigs/grant-helpdesk-5min?updateMask=disabled  {"disabled": true}
```

and re-enable when you are done. `gcloud dataform` does not exist in this SDK — drive the REST
API at `dataform.googleapis.com/v1beta1` with `gcloud auth print-access-token`.

**A local `dataform run` writes tables, not definitions.** The definitions the schedule uses come
from GitHub `main`. Testing locally proves nothing about what the next scheduled run will build.

**`grant_classification_feedback` is not in the `helpdesk` tag.** Tag-scoped runs never rebuild
it. After a rollback recreated it from an old definition it silently returned zero rows.

**Preview safely.** `HELPDESK_PREVIEW=1` repoints only `TICKETS_TABLE` and `META_TABLE` at a
`grant_helpdesk_preview` dataset while everything else reads live, so the app can be exercised
against a schema change without touching the desk. Build the preview with
`dataform run --schema-suffix=preview`; copy the Gemini-produced tables
(`grant_ticket_labels`, `grant_question_classifier`) across rather than re-running them.

**Deploying from the office network.** `gcloud run deploy` fails with SSL EOF against the
regional endpoint. Set `CLOUDSDK_API_ENDPOINT_OVERRIDES_RUN=https://run.googleapis.com/` to use
the global one — it works first time. Wrap it in a retry loop anyway;
`serviceusage.googleapis.com` times out intermittently.
