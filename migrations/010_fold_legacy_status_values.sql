-- Migration 010: Fold legacy 'new'/'assigned' status values down to 'open'.
--
-- The lifecycle is now binary: open (live) vs terminal (closed/cancelled/
-- not_a_question/confirmed_question). 'assigned' is no longer a status —
-- assignment moved to the orthogonal assigned_to column. 'new' was never
-- user-facing. Both collapse to 'open' (the inverse of migration 002's
-- open→new / in_progress→assigned rename). assigned_to is left untouched.
--
-- Preview first (read-only):
--
--   SELECT status, COUNT(*) AS n
--   FROM `bigtribebuilders.grant_helpdesk.ticket_metadata`
--   GROUP BY status ORDER BY n DESC;
--
-- Then run the UPDATE:

UPDATE `bigtribebuilders.grant_helpdesk.ticket_metadata`
SET status = 'open'
WHERE status IN ('new', 'assigned');
