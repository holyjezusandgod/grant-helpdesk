# Update: Thread-Aware Portal
**Date:** May 18, 2026  
**Who:** Martin + Claude  
**Status:** Built — ready to deploy

---

## What was the problem?

The helpdesk portal was treating every single comment or post as its own independent ticket. This caused two issues:

**1. Conversations were being split into separate tickets.**
When a grant coach asks a follow-up question like *"Which state are you from?"* and a member replies *"WI"* — that reply was either showing up as a new ticket of its own, or silently disappearing. The ongoing conversation had no single home. Coaches lost track of who still needed help.

**2. Answering a member auto-closed their ticket.**
The moment any team member commented or reacted to a post on Mighty Networks, the system marked that ticket as *Answered* and hid it from the portal. But a quick reply or a thumbs-up is not the same as actually resolving someone's question. Coaches had no way to keep a ticket visible until the member was truly helped.

---

## What did we change?

### Conversations now stay together
We taught the system what a "thread" actually is. Instead of treating every message as a separate ticket, it now recognises:

- A member's **post or article** is the start of a thread.
- A member's **first comment** on a post starts their own sub-thread within it.
- All **follow-up messages** — whether the member replies again or the coach asks a follow-up — belong to that same thread and are shown together.

This means coaches see the full conversation in one place, not scattered pieces.

### Closing is now a deliberate choice
Team engagement (commenting, reacting, replying) no longer automatically marks a ticket as done. Instead, coaches now have two options when they finish helping someone:

- **Answer** — marks the ticket as answered but keeps it visible. Use this if you want the team to see it was addressed.
- **Answer & Close** — marks it as done and removes it from the active queue.

The portal now only hides a ticket when a coach explicitly closes it.

### Closed threads can reopen automatically
If a member comes back and posts a new message after their ticket was closed, the ticket automatically reappears in the portal. No one falls through the cracks because a coach closed a thread too early.

---

## What stays the same?

- The AI still classifies every new message to check if it's a real grant question.
- Coaches can still assign, flag, and manage tickets exactly as before.
- The urgency system (Normal / Urgent / Critical based on how long a ticket has been open) is unchanged.

---

## What do coaches need to know?

- **"Answered" is now a manual status** you can set yourself from the dropdown — use it when you've replied but want to keep the ticket visible for a follow-up.
- **"Answer & Close"** is the new button in the ticket dialog — use it when the member is fully helped and the thread is done.
- Tickets you already closed in the past are still closed. This only changes how new closures work going forward.
- If a member you helped comes back and writes something new, their ticket will reappear automatically.

---

## When does this go live?

We're deploying this in the next session. No action needed from the team before then.

---

## Bug fix: Ticket dialog needed multiple reloads to open
**Reported by:** Grant coach team

### What was happening?
Coaches reported that clicking on a ticket sometimes showed a blank or empty dialog. Reloading the page two or three times would eventually make it appear correctly.

### What was causing it?
Three things were wrong under the hood:

**1. No loading indicator** — When a coach clicked a ticket, the app was silently querying the database in the background but showing nothing on screen while it did so. Coaches assumed the click had failed and reloaded. By the second or third attempt, the data was already cached and loaded instantly — making it look like a reload "fixed" it. In reality the first click had worked fine; it just needed a moment.

**2. Background thread was never cleaned up** — Every time a ticket dialog opened, a background task was spun up to load the conversation thread. That task was never properly closed after the dialog finished, quietly accumulating over a long session.

**3. No timeout or fallback on the thread loader** — If loading the conversation thread took too long (e.g. first database query of the day), the app would freeze silently with no way to recover.

### What we fixed
- Added a **"Loading ticket…" spinner** that shows immediately when a coach clicks a ticket.
- The background thread loader now always cleans up after itself using a proper `with` block.
- Added a **15-second timeout** on the thread loader — if it takes too long, the ticket still opens without the thread rather than freezing.
- Added a clear **error message** if the ticket itself fails to load, instead of a blank dialog.

### What coaches will notice
Just a small loading spinner when clicking a ticket — gone in under a second for most tickets. Everything else looks and works the same.

---

## Update: "Post Answer to MN" now marks the ticket as Answered

Previously, clicking **Post Answer to MN** only sent the reply to Mighty Networks — it did not change the ticket's status. Coaches had to separately set the status to "Answered" by hand.

Now, posting an answer automatically sets the ticket to **Answered** and keeps it visible in the portal. The workflow is:

- **Post Answer to MN** → reply is posted, ticket stays open with an "Answered" status
- **Answer & Close** → reply is posted and ticket is fully closed and removed from the queue

---

## Update: Visual separation between answered and unanswered tickets

Tickets that have been answered but are still open are now visually distinct from tickets waiting for a first reply:

- **Unanswered tickets** look exactly as before — white background, urgency dot (🟢 🟡 🔴) in the member column.
- **Answered tickets** get a soft green background and a **✓ Answered** badge in place of the urgency dot. The question text is slightly faded to signal the thread is less urgent.

This lets coaches scan the queue at a glance and focus on threads that still need a first reply.

---

## Fix: Portal was showing 600–800+ open tickets after deploy

After deploying the new thread-aware system, the portal briefly showed over 600 open tickets — far more than expected.

### What caused it
The new system removed the rule that auto-answered tickets when a team member commented or reacted. But thousands of old tickets had been relying on that rule to stay hidden. Once the rule was gone, they all resurfaced as open.

### What we did
Two fixes:

**1. Corrected the status logic** — the portal was defaulting every ticket without a manual status to "open", even when Dataform had already computed a proper status (like "answered" for historically engaged threads). Fixed so the Dataform-computed status is respected as the baseline, with manual overrides on top.

**2. Bulk-closed old tickets** — ran a one-time migration to close all 772 open tickets older than 7 days that had no manual status set. These were historical threads the team had already handled under the old system. Going forward, only tickets from the last 7 days and newer will remain visible unless manually reopened.

The portal now shows only recent, genuinely unresolved threads.

---

## New: Automatic Follow-up Questions (2026-05-18)

### What is it?

When a coach posts an answer to a member, they can now optionally schedule a follow-up question to be sent automatically — for example, a week later — asking the member if everything got resolved.

### How it works

In the answer section of any ticket there is a new checkbox: **"Schedule a follow-up question"**. If checked, two extra fields appear:

- **The follow-up message** — pre-filled with a friendly default, but fully editable. For example: *"Hi Sarah, just checking in — did everything get resolved? Feel free to reach out if there's anything else we can help with!"*
- **Days** — how many days to wait before sending (default: 7, max: 60).

When the coach clicks **Post Answer to MN**, the answer goes out immediately as normal. The follow-up is quietly scheduled in the background and sent automatically on the chosen day as a new comment on the same thread — it tags the member so they get a notification.

### When the follow-up is skipped automatically

If the member comes back and posts or replies in that thread before the follow-up is due, the follow-up is automatically cancelled. There is no point asking if everything was resolved when the conversation is already continuing.

### What coaches will see on the ticket list

Two small badges appear under a member's name after scheduling:

- **⏳ follow-up in Nd** — the follow-up is scheduled and counting down.
- **✅ follow-up sent** — the message has been posted.

No badge means either no follow-up was scheduled, or the member re-engaged and it was skipped automatically.

### What coaches need to do

The checkbox is opt-in — nothing changes for existing workflows. Use it when you want to check back with a member after some time. For straightforward questions that are clearly resolved, there is no need to schedule one.

---

## Deployment completed (2026-05-18)

All changes are now live in BigQuery and Dataform:

- **Migration 007** — `closed_at` and `closed_by` columns added to `ticket_metadata`
- **`stg_grant_member_comments`** — rebuilt with full-refresh (new `depth`, `reply_to_id`, `member_thread_rank` columns)
- **`stg_grant_candidates`** — rebuilt (only rank-1 member comments become tickets)
- **`grant_tickets`** — rebuilt (team engagement removed from status logic, reopen logic active)
- **Bulk migration** — 772 tickets older than 7 days closed in `ticket_metadata`
