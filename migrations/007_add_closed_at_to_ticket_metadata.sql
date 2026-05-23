-- Migration 007: add closed_at + closed_by to ticket_metadata
-- Run once before deploying the thread-aware portal changes.

ALTER TABLE `bigtribebuilders.grant_helpdesk.ticket_metadata`
  ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS closed_by STRING;
