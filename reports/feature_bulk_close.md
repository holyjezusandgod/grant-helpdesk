# Feature: Bulk Close
**Status:** Planned — not yet built  
**Requested by:** Misty Fowlds (leskocargrant@gmail.com)  
**Context:** Coaches answering directly in Mighty Networks create double work — resolved tickets stay open in the portal. Bulk Close lets Misty clean the queue during the transition period while the team is being trained on the portal workflow.

---

## Filters (combinable)

| Filter | What it does |
|---|---|
| By status | Close all tickets with status "Answered" |
| By grant coach | Close all tickets handled by a specific coach |
| Before a date | Close all tickets created or answered before a chosen date |
| Combination | e.g. "All Answered tickets by Sarah before May 15" |

## Options per bulk action
- **Skip automatic follow-ups** — do not schedule follow-up messages when bulk closing (for tickets resolved outside the portal)

## Hard rule
**Never bulk close a ticket with a pending follow-up question.** If a coach scheduled a follow-up, that decision is respected regardless of any bulk action. The preview count should show: "47 tickets will close (3 skipped — follow-up pending)".

## UX flow
1. "Bulk Close" button in portal toolbar opens a panel
2. Coach sets filters
3. Preview shows ticket count + skipped count
4. Confirm → tickets closed in one action

## Implementation notes
- Add bulk close panel to app.py (sidebar or top of ticket table)
- bq_client: `bulk_close_tickets(status, assigned_to, before_date)` — MERGE into ticket_metadata, status='closed', closed_by, closed_at
- Exclude any content_id present in followup_queue WHERE status='pending'
- No follow-up rows inserted for bulk-closed tickets
