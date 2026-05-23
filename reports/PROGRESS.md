# Lesko Help Desk — Progress Log

---

## 2026-04-22

### Train AI Tab
- Added a dedicated **Train AI** tab to the top navigation bar (between Reports and Settings)
- Removed `not_a_question` and `confirmed_question` from the main ticket Status filter — feedback statuses are now exclusive to the Train AI flow
- Train AI presents classifier rejects **one at a time** as a review queue:
  - Shows member name, content type, posted timestamp, MightyNetworks link, and full post body
  - Progress bar tracks reviewed vs remaining
  - **Incorrect — this IS a question** (left, black button / orange text) → marks post as `confirmed_question` and advances
  - **Correct — not a question** (right, black button) → marks post as `not_a_question` and advances
  - Queue reloads on demand once all items are handled
- "Reviewed" items are tracked via `ticket_metadata` — only posts with no manual status appear in the queue

### Dataform Model Changes
- `grant_content` — now includes **all** classified posts (`is_question = TRUE` and `FALSE`), not just classifier-accepted ones; adds `is_question` column
- `grant_tickets` — default `ticket_status` is now `not_a_question` when `is_question = FALSE` and no manual override exists
- Both tables rebuilt and deployed (`grant_content`: 40 MiB billed · `grant_tickets`: 50 MiB billed)

### Backend
- Added `get_unreviewed_rejects()` to `bq_client.py` — queries `grant_tickets` for `ticket_status = 'not_a_question' AND manual_status IS NULL`
