-- Migration 012: create space_names
-- space_id → space_name lookup for the Mighty Networks community. Populated
-- monthly by the sync-spaces Cloud Run Job (jobs/sync_spaces.py) from the MN
-- Admin API GET /networks/{id}/spaces. The app reads it (cached 24h) to show
-- which space/channel a ticket was commented in — in the portal list and the
-- answer dialog. Comments on a member's own profile carry space_id =
-- MN_NETWORK_ID and are labelled "Member bio" in the UI (mn_format.space_label),
-- so that id is not expected to appear here.
-- The job truncates and re-inserts on each run, so no unique constraint needed.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.space_names` (
  space_id     INT64     NOT NULL,  -- MN space id
  space_name   STRING    NOT NULL,  -- human-readable space/channel name
  refreshed_at TIMESTAMP NOT NULL   -- when this snapshot was written
);
