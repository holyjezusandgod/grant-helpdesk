-- 016 — Keep the recovered backlog out of the coaches' inbox.
--
-- Run alongside 015. Without this, the recovery lands ~1,288 NEW OPEN TICKETS in
-- the portal, all of them months old.
--
-- The rule: recovered content older than ONE WEEK is archived. Content from the
-- last seven days flows to the inbox as normal member activity. On the numbers
-- below that boundary falls between 2,813 rows and 2 — the backlog is old enough
-- that almost nothing sits near the line.
--
-- ── Why the existing cutoff does not cover this ──────────────────────────────
--
-- grant_tickets already has GENERAL_LANE_GO_LIVE, and it looks like the right
-- instrument, but read the CASE carefully: every one of its archived branches is
-- guarded by `lane = 'general'`. The question lane has no date rule at all — it
-- falls through to ELSE 'open'. So recovered content the classifier calls a
-- question becomes an open ticket no matter how old it is.
--
--   1,991 recovered rows reach the classifier
--   x 64.7% acceptance (7,240 classified, 4,683 questions, measured 2026-08-20)
--   = ~1,288 new open tickets
--
-- Measured against live data on 2026-08-20, simulating the post-fix population:
--
--   candidates after the fix                              8,168
--   already in the portal today                           5,355
--   newly appearing                                       2,815
--     older than a week -> archived by this migration     2,813
--       of which already closed by a coach earlier          740  (left untouched)
--       of which get an archived row from this migration   2,073
--     within the last week -> flows to the inbox normally      2
--
-- The 740 need a second look, because a closed ticket is not unconditionally
-- hidden: question-lane rule (4) reopens one when the member replied after
-- closure. Checked explicitly — 0 of the 740 have member activity later than
-- their closed_at, so none of them resurface. Re-run that check if this migration
-- is applied later than planned, since member activity accrues.
--
-- Widening GENERAL_LANE_GO_LIVE to both lanes would fix that and also silently
-- archive the coaches' CURRENT open queue, which is every bit as old. Not that.
--
-- ── The approach ─────────────────────────────────────────────────────────────
--
-- Pin the recovered rows to 'archived' in ticket_metadata. grant_tickets honours
-- an explicit status in BOTH lanes — general branch (1) and question branch (6) —
-- so one write covers both, needs no model change, and is reversible by deleting
-- the rows again. Archived content stays fully searchable; bq_reads.py only hides
-- it from the default view.
--
-- "Recovered" is defined as precisely as it can be: anything the portal does not
-- already know about. Snapshot first, compare after.

-- ── STEP 1 — BEFORE the full refresh, with the workflow config still paused ──
--
-- grant_tickets is a full-refresh table, so while the workflow is paused it holds
-- exactly what the portal shows today. Keep this table afterwards: it is the
-- permanent record of which rows the recovery auto-archived.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.recovery_snapshot_20260820` AS
SELECT DISTINCT content_id
FROM `bigtribebuilders.grant_helpdesk.grant_tickets`;

-- Sanity check before going further — expect roughly 5,588.
--
--   SELECT COUNT(*) FROM `bigtribebuilders.grant_helpdesk.recovery_snapshot_20260820`;

-- ── STEP 2 — AFTER `dataform run --full-refresh` on the three staging models, ──
-- ──          and BEFORE the workflow config is re-enabled                     ──
--
-- stg_grant_candidates is a view, so it reflects the refreshed staging tables the
-- moment the refresh finishes — no need to rebuild anything downstream first.
-- That is what lets this run before grant_tickets is ever built from the new
-- population, so the recovered rows are never briefly visible as open.
--
-- WHEN NOT MATCHED only: an existing metadata row means a coach has already acted
-- on that ticket, and their decision outranks this migration. One row per
-- content_id also matters because grant_tickets LEFT JOINs ticket_metadata
-- without deduplicating — a second row would fan the ticket out into duplicates.

MERGE `bigtribebuilders.grant_helpdesk.ticket_metadata` T
USING (
  SELECT c.content_id
  FROM `bigtribebuilders.grant_helpdesk.stg_grant_candidates` c
  LEFT JOIN `bigtribebuilders.grant_helpdesk.recovery_snapshot_20260820` s
    USING (content_id)
  WHERE s.content_id IS NULL
    -- Only content older than a week is held back. Anything from the last seven
    -- days is current member activity and belongs in the inbox.
    --
    -- Relative to CURRENT_DATE rather than a fixed date, deliberately: a
    -- hardcoded cutoff would start swallowing genuinely fresh content the moment
    -- the deploy slipped by a day, and this migration has already waited on two
    -- decisions. As written, whenever it runs it means the same thing.
    AND DATE(c.created_at) < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
) S
ON T.content_id = S.content_id
WHEN NOT MATCHED THEN INSERT
  (content_id, status, updated_at, closed_by)
VALUES
  (S.content_id, 'archived', CURRENT_TIMESTAMP(), 'migration/016 watermark recovery');

-- ── Verify ───────────────────────────────────────────────────────────────────
--
-- Re-enable the workflow, let one run rebuild grant_tickets, then confirm the
-- inbox did not move.
--
-- Expect new_and_open to equal ONLY the last-week rows this migration
-- deliberately let through — 2 when measured on 2026-08-20, and it will differ if
-- members post between now and the deploy. It must not be in the hundreds. If it
-- is, the archived write did not land: check that STEP 1 ran BEFORE the full
-- refresh, since a snapshot taken afterwards would contain the recovered rows
-- and this migration would treat them as already known.
--
--   SELECT
--     COUNTIF(t.ticket_status NOT IN ('closed','archived')
--             AND s.content_id IS NULL)                       AS new_and_open,
--     COUNTIF(t.ticket_status = 'archived'
--             AND s.content_id IS NULL)                       AS new_and_archived,
--     COUNTIF(t.ticket_status NOT IN ('closed','archived')
--             AND s.content_id IS NOT NULL)                   AS pre_existing_open
--   FROM `bigtribebuilders.grant_helpdesk.grant_tickets` t
--   LEFT JOIN `bigtribebuilders.grant_helpdesk.recovery_snapshot_20260820` s
--     USING (content_id);
--
-- Compare pre_existing_open against the coaches' open count from before the
-- deploy. It must be unchanged: this migration adds rows, it never re-labels one
-- the portal already had.
--
-- ── Undo ─────────────────────────────────────────────────────────────────────
--
-- Releases the whole recovered backlog into the inbox. Only if the team asks.
--
--   DELETE FROM `bigtribebuilders.grant_helpdesk.ticket_metadata`
--   WHERE closed_by = 'migration/016 watermark recovery';
--
-- To release it in stages instead, delete by date — oldest kept back, newest
-- first — so the queue grows at a pace the coaches choose:
--
--   DELETE FROM `bigtribebuilders.grant_helpdesk.ticket_metadata`
--   WHERE closed_by = 'migration/016 watermark recovery'
--     AND content_id IN (
--       SELECT content_id FROM `bigtribebuilders.grant_helpdesk.stg_grant_candidates`
--       WHERE DATE(created_at) >= '2026-07-01'
--     );
