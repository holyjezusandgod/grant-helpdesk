-- Migration 006: create team_feedback
-- Internal feedback/suggestions from the grant coaching team.
-- Each row is one submission; reply_text + replied_at are filled in by admin.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.team_feedback` (
  feedback_id   STRING    NOT NULL,
  submitted_by  STRING    NOT NULL,   -- current_user (email)
  feedback_type STRING    NOT NULL,   -- 'review', 'problem', 'suggestion'
  title         STRING    NOT NULL,
  body          STRING    NOT NULL,
  status        STRING    NOT NULL,   -- 'open', 'noted', 'done'
  reply_text    STRING,               -- admin reply
  replied_by    STRING,
  replied_at    TIMESTAMP,
  created_at    TIMESTAMP NOT NULL
);
