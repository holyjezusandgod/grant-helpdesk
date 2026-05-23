-- Migration 008: upcoming_events + rsvp_log tables

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.upcoming_events` (
  event_id      INT64       NOT NULL,
  title         STRING,
  starts_at     TIMESTAMP,
  ends_at       TIMESTAMP,
  time_zone     STRING,
  event_type    STRING,
  zoom_link     STRING,
  permalink     STRING,
  rsvp_enabled  BOOL,
  rsvp_closed   BOOL,
  refreshed_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.rsvp_log` (
  id          STRING      NOT NULL,
  content_id  STRING,
  event_id    INT64,
  member_id   STRING,
  rsvped_by   STRING,
  rsvped_at   TIMESTAMP
);
