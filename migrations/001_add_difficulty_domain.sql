-- Migration 001: Add difficulty and domain columns to ticket_metadata
-- Safe to run multiple times (BigQuery will error if column already exists,
-- so run each ALTER separately and skip any that fail).

ALTER TABLE `bigtribebuilders.grant_helpdesk.ticket_metadata`
  ADD COLUMN IF NOT EXISTS difficulty STRING,
  ADD COLUMN IF NOT EXISTS domain     STRING;
