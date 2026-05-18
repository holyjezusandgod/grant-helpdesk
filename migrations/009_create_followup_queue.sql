-- Migration 009: followup_queue table

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.followup_queue` (
  id             STRING      NOT NULL,
  ticket_id      STRING      NOT NULL,
  content_id     STRING      NOT NULL,
  content_type   STRING,
  member_id      STRING,
  member_name    STRING,
  message        STRING,
  send_after     TIMESTAMP,
  status         STRING,                -- pending / sent / skipped
  sent_at        TIMESTAMP,
  skipped_at     TIMESTAMP,
  skipped_reason STRING,
  scheduled_by   STRING,
  created_at     TIMESTAMP
);
