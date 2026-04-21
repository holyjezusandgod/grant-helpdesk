-- Migration 003: Verify grant_tickets view exposes required columns
--
-- Run this query. If content_type or first_engagement_at come back NULL
-- for ALL rows (not just some), the underlying table/view needs updating.

SELECT
    content_id,
    content_type,
    first_engagement_at,
    ticket_status,
    ticket_updated_at
FROM `bigtribebuilders.grant_helpdesk.grant_tickets`
LIMIT 10;

-- If content_type is missing from the view, add it in the view definition.
-- If first_engagement_at is missing, add it — it is needed for:
--   - Response time report  (bq_client.get_report_data("response_time"))
--   - KPI daily stats       (first_engagement_at IS NOT NULL filter)
--
-- Typical fix (adjust SELECT to match your base table):
--
-- CREATE OR REPLACE VIEW `bigtribebuilders.grant_helpdesk.grant_tickets` AS
-- SELECT
--     t.*,
--     m.status        AS manual_status,
--     m.assigned_to,
--     m.difficulty,
--     m.domain,
--     m.updated_at    AS ticket_updated_at,
--     -- add any missing columns from the raw source table below:
--     -- t.content_type,
--     -- t.first_engagement_at,
-- FROM `bigtribebuilders.grant_helpdesk.<raw_tickets_table>` t
-- LEFT JOIN `bigtribebuilders.grant_helpdesk.ticket_metadata` m
--     USING (content_id);
