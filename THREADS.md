# Thread Architecture — Issues & Design Notes

## Background

Currently every post, article, and comment is treated as a standalone ticket
with no relationship to other items. In practice they belong together: a post
is the root of a thread, and all its comments are children.

---

## Confirmed: data structure

Verified via query on `core_comments`:

- All comments have `targetable_type = 'Post'` and `targetable_id = post_id`
  regardless of visual nesting depth — everything points to the root post
- `depth` column is reliably populated: `1` = direct comment on post, `2` = reply to a comment
- `reply_to_id` is NULL for depth-1 comments and always set for depth-2 comments,
  pointing to the `comment_id` of the parent comment

| depth | count | reply_to_id |
|---|---|---|
| 1 | 5,710 | always NULL |
| 2 | 2,054 | always set |

This means thread grouping is simpler than expected:

| Content type | `thread_id` |
|---|---|
| Post | `CONCAT('post_', post_id)` — is its own root |
| Article | `CONCAT('article_', article_id)` — is its own root |
| Comment (any depth) | `CONCAT('post_', targetable_id)` — always resolves to root post |

No multi-hop joins needed. `targetable_id` is always the thread root.

---

## Issues to solve

### 1. Add `thread_id` to the pipeline

**Problem:** No `thread_id` column exists anywhere in the current pipeline.
Items have no link to their thread.

**What needs to change:**
- Add `thread_id` to `stg_grant_member_comments`:
  `CONCAT('post_', CAST(targetable_id AS STRING)) AS thread_id`
- Add `thread_id` to `stg_grant_posts` and `stg_grant_articles`:
  `content_id AS thread_id` (they are their own root)
- Propagate through `stg_grant_candidates` → `grant_content` → `grant_tickets`

**This is the foundation for all other issues below.**

---

### 2. "answered" signal for comment tickets ✅ DONE

**Was:** `stg_team_engagement` only detected team comments on posts. A team
reply to a member comment fired the signal on the root post ticket, leaving
the comment ticket stuck as `open`.

**Fix (shipped 2026-04-23):** Added `team_comment_replies` CTE to
`stg_team_engagement`. When a team member posts a depth-2 comment with
`reply_to_id` set, the signal resolves to `CONCAT('comment_', reply_to_id)` —
the exact comment ticket that was answered. `grant_tickets` now includes
`team_comment_replied` in the answered CASE alongside `team_commented` and
`team_reacted`.

---

### 3. Multi-member threads

**Problem:** A single thread can contain questions from multiple different
members. For example: a host posts an article and three members each ask a
question in the comments. These are three independent help requests.

**Design decision (already resolved):**
- Tickets stay at the individual question level — threads are context only
- Each ticket keeps its own `member_id`, assignment, and status
- `thread_id` links them for display/grouping purposes only
- Each member's helper assignment is independent of other members in the thread

**Remaining UI question:** The ticket list could optionally group rows by
`thread_id`. Needs a design decision on whether that's wanted.

---

### 4. Root post is not a question

**Problem:** A host posts an informational article (`is_question = FALSE`).
All tickets live in the comments. The `thread_id` points to a content item
that has no ticket of its own. The pipeline handles this fine — `thread_id`
does not need to be a ticket — but the **UI needs to handle it**:

- The ticket dialog should be able to fetch and display the root post body
  as thread context even when the root is not itself a ticket
- Query: `SELECT body FROM grant_content WHERE content_id = thread_id`

---

### 5. Historical backfill

**Problem:** Existing tickets have no `thread_id`. Once the column is added,
existing rows need to be backfilled.

**Approach (simple, no multi-hop needed):**
- Comment tickets: `thread_id = CONCAT('post_', targetable_id)` — direct from
  `core_comments`
- Post/article tickets: `thread_id = content_id`

Can be done as a one-time migration after the Dataform column is added.

---

## Suggested build order

1. ~~Fix "answered" signal for comment tickets~~ ✅ Done 2026-04-23
2. Add `thread_id` to staging models and propagate to `grant_tickets` **(#1)**
   — foundation for everything else, low risk
3. Backfill `thread_id` on existing tickets **(#5)**
4. Add thread context panel in the ticket dialog **(#4)**
   — UI only, no pipeline change, immediately useful
5. Decide on thread grouping in the ticket list **(#3)**
