-- Migration 004: create member_assignment_overrides
-- Stores explicit helper overrides set from the UI.
-- One row per member; MERGE upserts on save.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.member_assignment_overrides` (
  member_id   INT64     NOT NULL,
  assigned_to STRING    NOT NULL,
  updated_at  TIMESTAMP NOT NULL,
  updated_by  STRING
);
