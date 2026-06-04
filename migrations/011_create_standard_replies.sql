-- Migration 011: create standard_replies
-- Reusable answer templates shared by the grant coaching team.
-- Coaches manage them in the 📋 Replies tab; the answer dialogs offer an
-- "Insert standard reply" dropdown that appends the body to the answer box.
-- Rows are never hard-deleted — archiving sets is_active = FALSE.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.standard_replies` (
  reply_id    STRING    NOT NULL,  -- uuid4
  title       STRING    NOT NULL,  -- shown in the dropdown
  body        STRING    NOT NULL,  -- appended into the answer box (may be multi-line)
  is_active   BOOL      NOT NULL,  -- FALSE = archived, hidden everywhere
  created_by  STRING    NOT NULL,  -- coach email
  created_at  TIMESTAMP NOT NULL,
  updated_by  STRING,              -- last editor (email)
  updated_at  TIMESTAMP
);
