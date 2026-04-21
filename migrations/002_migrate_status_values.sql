-- Migration 002: Rename status values in ticket_metadata to new 4-value enum
--
--   open        → new
--   in_progress → assigned
--   answered    → closed
--   (cancelled is new — no existing rows to migrate)
--
-- Preview first (read-only):
--
--   SELECT status, COUNT(*) AS n
--   FROM `bigtribebuilders.grant_helpdesk.ticket_metadata`
--   GROUP BY status ORDER BY n DESC;
--
-- Then run the UPDATE:

UPDATE `bigtribebuilders.grant_helpdesk.ticket_metadata`
SET status = CASE
    WHEN status = 'open'        THEN 'new'
    WHEN status = 'in_progress' THEN 'assigned'
    WHEN status = 'answered'    THEN 'closed'
    ELSE status
END
WHERE status IN ('open', 'in_progress', 'answered');
