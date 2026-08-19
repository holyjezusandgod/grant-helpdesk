-- Migration 014: create team_member_overrides
--
-- Who counts as "the team" was decided entirely by Mighty Networks:
-- network_role IN ('host', 'moderator'). That is 20 people out of 29,929, and
-- it cannot express "this member acts as a host even though MN never gave them
-- the role". Note the role we CANNOT use for this: 'contributor' is 27,278
-- members — it is the default for everyone, not an elevated permission.
--
-- This table is that missing override list. It is unioned with the MN roles in
-- stg_grant_team_members, which is now the single definition of "team" for the
-- whole pipeline. Being on it means, everywhere at once:
--   - your own posts and comments stop becoming tickets
--   - your comments and reactions count as TEAM ENGAGEMENT on other people's
--     threads (team_commented / team_reacted / first_engagement_at)
--   - your reply to a closed ticket no longer auto-reopens it
--
-- Rows are added by hand. active = FALSE rather than DELETE, so the reason a
-- person was ever on the list survives.

CREATE TABLE IF NOT EXISTS `bigtribebuilders.grant_helpdesk.team_member_overrides` (
  member_id  INT64     NOT NULL,  -- MN member id
  full_name  STRING,              -- for humans reading the table; not joined on
  reason     STRING    NOT NULL,  -- why this person is treated as team
  active     BOOL      NOT NULL,  -- FALSE retires the override without losing it
  added_by   STRING,              -- who made the call
  added_at   TIMESTAMP NOT NULL
);

-- Michelle Cairns — MN role is 'contributor' (the default), but she works the
-- community like a host: 290 comments across 224 threads since 2026-02-24, and
-- her own posts are greetings and encouragement rather than grant questions.
-- Martin's call, 2026-08-19.
MERGE `bigtribebuilders.grant_helpdesk.team_member_overrides` T
USING (
  SELECT 12583063 AS member_id, 'Michelle Cairns' AS full_name,
         'Acts as a host/moderator in the community; MN role is only the default contributor' AS reason,
         TRUE AS active, 'martin.j.menke@gmail.com' AS added_by, CURRENT_TIMESTAMP() AS added_at
) S
ON T.member_id = S.member_id
WHEN NOT MATCHED THEN INSERT
  (member_id, full_name, reason, active, added_by, added_at)
VALUES
  (S.member_id, S.full_name, S.reason, S.active, S.added_by, S.added_at);

-- ── Retiring content that is already staged ──────────────────────────────────
-- Adding someone here stops their FUTURE content becoming tickets, but it does
-- not remove what is already staged: stg_grant_posts / _articles /
-- _member_comments are incremental and only ever append.
--
-- Do NOT reach for `dataform run --full-refresh` to fix that. A full rebuild of
-- those three models adds ~3,960 rows production has never had — the incremental
-- predicate is `created_at > MAX(created_at)`, a watermark that permanently
-- skips anything arriving with an older timestamp (~2,862 member comments from
-- Feb-Jul 2026 alone). That is a real pre-existing gap, worth fixing on its own
-- terms, but it must not ride along with a team override.
--
-- So retire the rows surgically instead. Re-runnable, and safe to run again
-- after adding anyone new to the override table.
--
-- Preview first (read-only):
--
--   SELECT 'posts' src, COUNT(*) FROM `bigtribebuilders.grant_helpdesk.stg_grant_posts`
--   WHERE member_id IN (SELECT member_id FROM `bigtribebuilders.grant_helpdesk.team_member_overrides` WHERE active);

DELETE FROM `bigtribebuilders.grant_helpdesk.stg_grant_posts`
WHERE member_id IN (
  SELECT member_id FROM `bigtribebuilders.grant_helpdesk.team_member_overrides` WHERE active
);

DELETE FROM `bigtribebuilders.grant_helpdesk.stg_grant_articles`
WHERE member_id IN (
  SELECT member_id FROM `bigtribebuilders.grant_helpdesk.team_member_overrides` WHERE active
);

DELETE FROM `bigtribebuilders.grant_helpdesk.stg_grant_member_comments`
WHERE member_id IN (
  SELECT member_id FROM `bigtribebuilders.grant_helpdesk.team_member_overrides` WHERE active
);
