-- 015 — Move state-dependent logic out of the append-only staging models.
--
-- Supersedes the "Retiring content that is already staged" section of
-- 014_create_team_member_overrides.sql. See the warning at the bottom: those
-- DELETE statements must NOT be run again.
--
-- ── What changed in the models ───────────────────────────────────────────────
--
-- stg_grant_posts / _articles / _member_comments are incremental and append-only:
-- a row is written once and never revisited. Three rules that can change the
-- answer for an already-written row had been living inside them, and each one
-- silently froze:
--
--   1. The incremental watermark keyed on created_at (when a member wrote the
--      content) instead of received_at (when we learned of it). Anything arriving
--      late or back-dated fell below the high-water mark and was refused forever.
--      Measured loss: 1,926 rows, 2026-02-01 to 2026-03-18, never seen by a coach.
--      Now keys on received_at with one hour of overlap; the MERGE that uniqueKey
--      produces makes the re-read idempotent (verified against 343 MERGE jobs in
--      production job history, not assumed).
--
--   2. The team/avatar exclusion. stg_grant_team_members follows a member's
--      CURRENT Mighty Networks role, so it must be re-applied on every run. Frozen
--      into staging it was not: member 6458470 held moderator until 2026-07-21,
--      and their 1,645 posts and comments stayed invisible to the desk after they
--      stepped down. Moved to stg_grant_candidates, which is a view.
--
--   3. member_thread_rank. A window function inside an incremental model only sees
--      the rows in the current batch, so a member's second comment on a post
--      arrived later, found an empty partition, and was ranked 1 again — a
--      duplicate ticket for one conversation. 349 such rows existed. Also moved to
--      stg_grant_candidates, where the window spans the whole table.
--
-- The rule going forward: an append-only model may only do ROW-LOCAL work. If it
-- depends on other rows or on current state, it belongs in the view.
--
-- ── One-time recovery — MANDATORY, NOT OPTIONAL ──────────────────────────────
--
-- This is not merely how the lost rows come back; it is the only way the new
-- models can run at all. The schema changed in all three: received_at was added,
-- and member_thread_rank was removed from the comments model. Dataform builds an
-- incremental MERGE's column list from the EXISTING table, so against today's
-- tables it emits `update set member_thread_rank = S.member_thread_rank` for a
-- column the new query no longer produces:
--
--   bigquery error: Name member_thread_rank not found inside S
--
-- Caught by `dataform run --dry-run --tags helpdesk` before any of this shipped.
--
-- This makes the ORDER load-bearing. A release config compiles main HOURLY and
-- the workflow runs every 30 MINUTES, so merging to main is itself the trigger:
-- push without pausing and a scheduled run will pick up the new definitions
-- against the old tables within the hour and fail. Pause first.
--
-- No SQL here — this is a Dataform operation, and it must be the only thing
-- moving at the time. With the workflow config paused (see the repo notes on the
-- hourly-release / 30-minute-run mismatch):
--
--   dataform run --full-refresh --actions stg_grant_posts stg_grant_articles \
--                                        stg_grant_member_comments
--
-- Staging then mirrors core_* one-for-one. grant_question_classifier picks up the
-- recovered rows on its own: its incremental predicate is a set difference
-- (content_id NOT IN self), not a timestamp, so age does not matter.
--
-- Expected effect, measured 2026-08-20 before the change:
--   candidates             5,588 -> 8,166
--   new Gemini classifications                     1,991
--   of those created before GENERAL_LANE_GO_LIVE   1,990  (land archived, not on coaches)
--   of those belonging to 6458470 + 12523611       1,261  (see below)
--
-- assert_staging_complete will FAIL until the full refresh has run. That is the
-- assertion doing its job, not a regression.
--
-- ── Optional, and a judgement call for Martin and Lise ────────────────────────
--
-- After change 2, "team" means team AS OF NOW. Members 6458470 and 12523611 are
-- contributors today but were acting as team when they wrote most of their
-- content, so it would now flow into the desk as member questions. network_role
-- has no history, so as-of-write-time is not available from the data.
--
-- The overrides table is exactly the instrument for this. It marks them as team
-- permanently and drops the classifier cost from 1,991 rows to ~730.
--
-- DECIDED BY MARTIN, 2026-08-20: treat both as team. Applied as part of the
-- deploy, BEFORE the full refresh, so their content never enters the candidate
-- pool at all rather than entering and being archived afterwards. Checked first:
-- between them they had 2 live tickets and both were already archived, so no
-- coach lost anything from the inbox.

MERGE `bigtribebuilders.grant_helpdesk.team_member_overrides` T
USING (
  SELECT 6458470 AS member_id, 'Former moderator (role removed 2026-07-21, since left)' AS full_name,
         'Held host/moderator while writing; content is staff, not member questions' AS reason,
         TRUE AS active, 'martin.j.menke@gmail.com' AS added_by, CURRENT_TIMESTAMP() AS added_at
  UNION ALL
  SELECT 12523611, 'Former moderator (role removed ~2026-08-11)',
         'Held host/moderator while writing; content is staff, not member questions',
         TRUE, 'martin.j.menke@gmail.com', CURRENT_TIMESTAMP()
) S
ON T.member_id = S.member_id
WHEN NOT MATCHED THEN INSERT
  (member_id, full_name, reason, active, added_by, added_at)
VALUES
  (S.member_id, S.full_name, S.reason, S.active, S.added_by, S.added_at);
--
-- ── DO NOT RE-RUN THE DELETE BLOCK IN 014 ────────────────────────────────────
--
-- 014 deleted override members' rows straight out of the staging tables, because
-- back then staging was supposed to hold member content only and had no way to
-- un-stage anyone. That is no longer true: staging now mirrors core_* deliberately
-- and the exclusion happens one hop downstream in stg_grant_candidates.
--
-- Running those DELETEs now would remove rows the pipeline is meant to hold,
-- assert_staging_complete would flag them as missing, and the received_at
-- watermark — long past their arrival — would never bring them back. Adding
-- someone to team_member_overrides is now sufficient on its own, and takes effect
-- on the next run for their whole history, past and future.
