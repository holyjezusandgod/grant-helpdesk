-- Migration 013: give ticket_metadata its own `lane` column.
--
-- Until now "is this a question?" and "where is this ticket in its lifecycle?"
-- shared one column. `status` held both lifecycle values (open/answered/closed/
-- cancelled/flagged) AND the two classifier-feedback markers (not_a_question,
-- confirmed_question). That conflation had a real cost: closing a rejected item
-- overwrote the not_a_question marker, so the row silently dropped out of
-- grant_classification_feedback and the classifier never learned from it.
--
-- lane is now its own column: 'question' | 'general' | NULL (NULL = no coach has
-- overridden the classifier, so grant_tickets falls back to is_question).
--
-- RUN ORDER — steps 1 and 2 are safe to run against the live app; step 3 is NOT.
--
--   step 1 + 2  →  deploy Dataform (helpdesk tag)  →  step 3  →  deploy the app
--
-- Steps 1 and 2 only add information, so the current app and the current
-- grant_classification_feedback keep working untouched while they run. Step 3
-- clears the legacy markers out of `status`, and the OLD feedback view keys on
-- exactly those markers — so it must not run until the new view (which keys on
-- lane) is live.

-- ── Step 1: add the column ────────────────────────────────────────────────────
ALTER TABLE `bigtribebuilders.grant_helpdesk.ticket_metadata`
ADD COLUMN IF NOT EXISTS lane STRING;

-- ── Step 2: backfill lane from the legacy status markers ──────────────────────
-- Preview first (read-only):
--
--   SELECT status, COUNT(*) AS n
--   FROM `bigtribebuilders.grant_helpdesk.ticket_metadata`
--   WHERE status IN ('not_a_question', 'confirmed_question')
--   GROUP BY status;

UPDATE `bigtribebuilders.grant_helpdesk.ticket_metadata`
SET lane = CASE status
             WHEN 'not_a_question'     THEN 'general'
             WHEN 'confirmed_question' THEN 'question'
           END
WHERE status IN ('not_a_question', 'confirmed_question');

-- ── Step 3: clear the legacy markers out of status ────────────────────────────
-- ONLY after the new grant_classification_feedback view is live.
-- status goes NULL, which means "no manual lifecycle override" — grant_tickets
-- then derives the status from the lane, exactly as it does for a fresh row.

UPDATE `bigtribebuilders.grant_helpdesk.ticket_metadata`
SET status = NULL
WHERE status IN ('not_a_question', 'confirmed_question')
  AND lane IS NOT NULL;
