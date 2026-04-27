# UI Design Brief — Lesko Help Desk

This file is for the designer working on the Lesko Help Desk UI.
Share your mockup in the Claude chat and Claude will implement it directly into the app.

---

## How to work with Claude on this

1. Open the `grant-helpdesk` repo in Claude Code
2. Share your mockup (image, PDF, or Figma screenshot) in the chat
3. Tell Claude which screen(s) the mockup covers
4. Claude will implement it and restart the app so you can review it live at `http://localhost:8501`
5. Give feedback in the chat — Claude will iterate

---

## Screens in the app

There are four main screens. Design one or all of them.

| Screen | Description |
|---|---|
| **Login page** | Shown before Google login. Currently a blue gradient card with a "Sign in with Google" button |
| **Ticket list** | Main view — sidebar filters on the left, KPI metrics at the top, table of tickets below |
| **Ticket dialog** | Popup when you click a ticket — shows the full thread, member info, status/assignee controls, and the answer box |
| **Settings tab** | Where team members add their Mighty Networks API key |

---

## Brand colours

These are already in the app — use them in your mockup or propose new ones.

| Name   | Hex       | Currently used for         |
|--------|-----------|----------------------------|
| Indigo | `#4a52a3` | Primary / sidebar / header |
| Yellow | `#f5c520` | Urgent tickets             |
| Green  | `#2e9b2e` | Answered / closed / normal |
| Blue   | `#2d6ee0` | Open tickets               |
| Red    | `#e03c3c` | Critical / cancelled       |

Sidebar background: `#1e2a5e` (deep navy)
Main background: `#ffffff` (white)

---

## Domain icons

Each ticket has a domain tag with an emoji icon. These are fixed — don't redesign them away.

| Domain | Icon |
|---|---|
| Pay Debt & Bills | 💰 |
| Home & Housing Help | 🏠 |
| Cars & Car Repairs | 🚗 |
| Healthcare Assistance | 🏥 |
| Start A Business | 🚀 |
| Launch A Nonprofit | 🤲 |
| Boost Your Career | 💼 |
| Taxes Help Guidance | 🧾 |
| Find Legal Help | ⚖️ |
| Family & Children | 👨‍👩‍👧 |
| Seniors & Disabilities | 🛡️ |
| Programs for Veterans | 🎖️ |
| Community Support | 🤝 |
| Other | 📌 |

---

## Ticket statuses

Tickets have one of these statuses — each needs a visual treatment (colour, badge, icon).

| Status | Meaning |
|---|---|
| `open` | Needs a response |
| `answered` | Team has responded on Mighty Networks |
| `closed` | Manually closed |
| `cancelled` | Not relevant |

---

## Urgency levels

Based on how long the ticket has been open.

| Urgency | Meaning |
|---|---|
| `normal` | Less than 24 hours old |
| `urgent` | 24–48 hours old |
| `critical` | More than 48 hours old |

---

## What you CAN change

- Colours, typography, spacing, icons
- Layout of the ticket list (e.g. cards instead of a table)
- The ticket dialog layout and information hierarchy
- The login page design
- The header/banner style
- Sidebar appearance

---

## What you CANNOT change (technical constraints)

- **Streamlit layout system** — the app uses columns and vertical blocks. Elements cannot be placed at arbitrary pixel positions. Very freeform layouts may need to be adapted.
- **The data fields** — you can reorder or hide fields visually but cannot add new data without a backend change
- **Google login** — the OAuth flow is fixed; only the page around the button can be styled
- **Font loading** — custom fonts require a CDN link; system fonts (sans-serif, serif, monospace) work out of the box

---

## How to give Claude your mockup

Just paste or drag the image into the Claude chat and say which screen it covers. Example:

> "Here is my mockup for the ticket list. I want cards instead of a table, with the domain icon large on the left and the status badge top right."

Claude will:
1. Read the current code to understand the existing structure
2. Implement your design in `app.py` using Streamlit layout + custom CSS
3. Restart the app at `http://localhost:8501` so you can review it live
4. Adjust based on your feedback

---

## File locations (for reference)

| File | What it controls |
|---|---|
| `app.py` | All UI layout, components, and CSS |
| `config.py` | Colour constants, domain lists, status lists |
| `.streamlit/config.toml` | Theme base, primary colour, background colour |
| `bq_client.py` | Data — do not touch unless adding new data fields |
