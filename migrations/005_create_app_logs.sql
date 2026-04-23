-- Migration 005: create app_logs
-- Stores error events from external service calls (e.g. Dataform trigger failures).
-- Written by the app via streaming insert; never managed by Dataform.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.app_logs` (
  log_id     STRING    NOT NULL,
  created_at TIMESTAMP NOT NULL,
  level      STRING    NOT NULL,  -- 'ERROR', 'WARNING', 'INFO'
  source     STRING    NOT NULL,  -- function or component that logged the event
  message    STRING    NOT NULL,
  detail     STRING              -- stack trace or extra context
);
