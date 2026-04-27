# Lesko Help Desk — v0.1 Specification
> Derived from voice transcript · Target codebase: `app.py` / `bq_client.py` / `config.py`

---

## 1. Rename

| Before | After |
|--------|-------|
| `Grant Help Desk` | `Lesko Help Desk` |

Update: page title, sidebar heading, `st.set_page_config`, any string literals.

---

## 2. Authentication — Replace "You are" dropdown

**Current behaviour:** A `st.selectbox` lets the user pick their own name.

**New behaviour:** The logged-in user's identity is read from the session automatically (e.g. Streamlit Community Cloud `st.experimental_user`, or a lightweight SSO/env-var approach). The name is **displayed** in the sidebar but **not editable**. Remove the selector entirely.

> Implementation note: if a proper auth layer is not yet available, fall back to an env-var `LESKO_USER` and show a read-only `st.text` widget. The point is that users **cannot impersonate another team member**.

---

## 3. Ticket Status Values

Replace the current three statuses with four:

| Value | Label |
|-------|-------|
| `new` | 🆕 New |
| `assigned` | 🟡 Assigned |
| `closed` | 🟢 Closed |
| `cancelled` | ⛔ Cancelled |

Update all references in `app.py`, `bq_client.py`, SQL queries, and `STATUS_ICON` mapping.

---

## 4. Urgency — Auto-calculated Field

Urgency is **never set manually**; it is derived from the age of the ticket at display time.

| Age since `created_at` | Urgency | Colour indicator |
|------------------------|---------|-----------------|
| < 24 h | Normal | 🟢 |
| 24 h – 48 h | Urgent | 🟠 |
| > 48 h | Critical | 🔴 |

Add a computed column `urgency` in `bq_client.get_tickets()` using BigQuery's `TIMESTAMP_DIFF`.

---

## 5. Difficulty Level Field

A manually assigned field on each ticket. Allowed values:

- `easy`
- `intermediate`
- `advanced`
- `inappropriate`

Store in `ticket_metadata` (add column if missing). Surfaced as a `st.selectbox` in the ticket detail popup.

> Rationale: allows routing hard tickets to senior team members and filtering out inappropriate ones.

---

## 6. Domain Field

A manually assigned field on each ticket representing the **question topic**. Examples:

- `housing`, `childcare`, `car_repairs`, `pay_bills`, `healthcare`, …

The list of valid domains must be **configurable** (add `DOMAINS` list to `config.py`). Surfaced as a `st.selectbox` in the ticket detail popup and as a sidebar filter.

---

## 7. Sidebar Filters

Replace the current filters with the following set (in order):

| # | Filter | Widget type |
|---|--------|-------------|
| 1 | **Status** | `selectbox` — All / New / Assigned / Closed / Cancelled |
| 2 | **Date range** | `radio` — Today / This week / This month / Custom; show `date_input` (range) when Custom selected |
| 3 | **Assigned to** | `selectbox` — All + team members |
| 4 | **Member ID** | `text_input` — free-form numeric entry |
| 5 | **Urgency** | `selectbox` — All / Normal / Urgent / Critical |
| 6 | **Difficulty** | `selectbox` — All / Easy / Intermediate / Advanced / Inappropriate |
| 7 | **Domain** | `selectbox` — All + domain list from `config.DOMAINS` |

All filters pass to `bq_client.get_tickets()` which builds the `WHERE` clause dynamically.

---

## 8. KPI Bar (Top of Main Area)

Replace the current 4-metric row with two rows:

### Row A — Open ticket breakdown

```
[ 🆕 Open: 600  |  🟢 Normal: 300  |  🟠 Urgent: 200  |  🔴 Critical: 100 ]
```

All four values come from a single aggregation query filtered to status = `new` or `assigned`.

### Row B — Daily productivity

```
[ 📥 In today: N  |  ✅ Answered today: N  |  📈 Daily avg: N  |  🎯 Goal progress: N / goal ]
```

- **In today**: tickets with `created_at` on today's date.
- **Answered today**: tickets whose status changed to `closed` today (needs `ticket_updated_at`).
- **Daily avg**: rolling 30-day average of tickets closed per day.
- **Goal progress**: answered today vs. a configurable constant `DAILY_GOAL` in `config.py`.

Add a `get_daily_stats()` function in `bq_client.py`.

---

## 9. Main List View — Table Layout

Replace the current card-based list with a **`st.dataframe` or `st.data_editor` table**. Each row = one ticket.

Columns to display:

| Column | Notes |
|--------|-------|
| Timestamp | `created_at` — show date **and** time (`YYYY-MM-DD HH:MM`) |
| Member name | Clickable: clicking fills the **Member ID** sidebar filter and reruns |
| Question preview | First ~120 chars of `body` |
| Assigned to | Editable dropdown inline (`st.data_editor`) or via popup |
| Difficulty | Display value |
| Urgency | Auto-calculated; show coloured badge |
| Status | Display value with icon |
| Community link | `st.link_button` or clickable 🔗 icon pointing to `permalink` |

Clicking anywhere on a row (except the member name and community link) opens the **ticket detail popup**.

---

## 10. Ticket Detail — Popup / Expanded Panel

Triggered by clicking a row. Open as `st.dialog` (Streamlit ≥ 1.32) or right-panel expansion.

Contents (in order):

1. **Header**: member name, status badge, urgency badge, content type (`post` vs `comment` — from `content_type` field).
2. **Metadata row**: state, city, member ID, posted at, link to MightyNetworks profile.
3. **Full question body** in a scrollable `st.container` with `height=` parameter; user can expand further.
4. **Editable fields**: status, assigned-to, difficulty, domain — save via `bq_client.update_ticket_meta()`.
5. **Answer entry field**: `st.text_area` with a **Post** button. Submitting inserts a record into `ticket_comments` via `bq_client.post_comment()`. Multiple responses per ticket are allowed.
6. **Internal comment thread**: existing comments displayed in chronological order (unchanged from current).
7. **Call Sheet Report button** *(UI stub for now)*: opens a sub-dialog or expander with pre-filled fields: `state`, `zip_code`, `domain`. Executes a predefined prompt template (prompt content TBD — wire up later).
8. **Member history expander**: unchanged from current.

---

## 11. Future Features — Placeholders Only

Add these as **disabled buttons or `st.caption` notes** so the UI real estate is reserved:

| Feature | Placeholder location |
|---------|---------------------|
| AI-generated answer | Button in ticket detail, disabled, tooltip "Coming soon" |
| Predefined answers | Dropdown in ticket detail, disabled |
| Excel export | Button in Reports tab, disabled |

---

## 12. Reports Tab

Add a **Reports** tab (or top-level nav item alongside the main view). Contains four report sections:

### 12.1 Volume report
- Tickets asked vs. tickets answered, per day/week/month (selectable).
- Display as a line or bar chart (`st.bar_chart`).

### 12.2 Response time report
- Distribution of time-to-first-response (difference between `created_at` and `first_engagement_at`).
- Show average, median, and % answered within SLA (< 24 h).

### 12.3 Team productivity report
- Count of tickets closed (`closed` status) per team member, for a selectable date range.
- Display as a horizontal bar chart.

### 12.4 Domain breakdown report
- Count of tickets per domain for a selectable period.
- Display as a pie or bar chart.

Add a `get_report_data(report_type, date_from, date_to)` function in `bq_client.py`.

---

## 13. App Settings / Three-dot Menu

This is an **in-house internal tool** — not publicly accessible. Remove or hide anything irrelevant:

- No "Sign up", "Pricing", or public-facing links.
- Keep: dark/light theme toggle, "About" (show app version `v0.1`), "Report a bug" (internal Slack link or email).
- Add `config.py` constant: `APP_VERSION = "0.1"`.

---

## 14. config.py additions

```python
APP_VERSION  = "0.1"
APP_NAME     = "Lesko Help Desk"
DAILY_GOAL   = 50  # target tickets closed per day

DOMAINS = [
    "housing", "childcare", "car_repairs", "pay_bills",
    "healthcare", "food", "transportation", "education", "other",
]

DIFFICULTY_LEVELS = ["easy", "intermediate", "advanced", "inappropriate"]

TICKET_STATUSES = ["new", "assigned", "closed", "cancelled"]
```

---

## 15. BigQuery / Schema changes required

| Table | Change |
|-------|--------|
| `ticket_metadata` | Add columns: `difficulty VARCHAR`, `domain VARCHAR` |
| `grant_tickets` view | Ensure `content_type` (`post` / `comment`) is exposed |
| `grant_tickets` view | Ensure `first_engagement_at` is exposed |
| `ticket_metadata` | Rename `status` values to match new four-value enum (migration script needed) |

---

## 16. Out of scope for v0.1

- AI answer generation
- Predefined answer library
- Excel / CSV export
- Public-facing access or user account management
