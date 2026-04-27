# Onboarding — Lesko Help Desk

This guide sets up your local development environment for the Lesko Help Desk dashboard. Follow every step in order.

---

## What this project is

A Streamlit dashboard for managing the Lesko grant support queue. It reads from BigQuery (GCP project `bigtribebuilders`, dataset `grant_helpdesk`) and uses Dataform to transform community data into helpdesk tickets.

**Stack:**
- Python + Streamlit (dashboard)
- Google BigQuery (data store)
- Dataform (data pipeline, GitHub-connected)
- Google OAuth (login)

---

## Step 1 — Prerequisites

Make sure you have the following installed:

```bash
# Python 3.11+
python3 --version

# Google Cloud CLI
gcloud --version

# Git
git --version
```

If `gcloud` is missing, install it from: https://cloud.google.com/sdk/docs/install

---

## Step 2 — Clone the repository

```bash
git clone https://github.com/[ASK_MARTIN_FOR_REPO_URL]/grant-helpdesk.git
cd grant-helpdesk
```

---

## Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Authenticate with Google Cloud

This gives your local machine (and Claude Code) access to BigQuery and Dataform.

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project bigtribebuilders
```

When prompted, sign in with `giulia.gaianet@gmail.com`. Your account already has the following roles on the `bigtribebuilders` project:
- `roles/bigquery.dataEditor` — read/write BigQuery tables
- `roles/bigquery.jobUser` — run BQ queries
- `roles/dataform.editor` — edit and run Dataform pipelines

---

## Step 5 — Create the Streamlit secrets file

This file holds the Google OAuth credentials for the login screen. It is **not in git** (gitignored) so you need to create it manually.

Create the file at `.streamlit/secrets.toml`:

```bash
mkdir -p .streamlit
```

Then create `.streamlit/secrets.toml` with the following content (ask Martin for the actual client ID and client secret):

```toml
[auth]
redirect_uri  = "http://localhost:8501/oauth2callback"
cookie_secret = "any-random-32-character-string-you-choose"

[auth.google]
client_id     = "ASK_MARTIN"
client_secret = "ASK_MARTIN"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

For `cookie_secret`, generate a random string:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 6 — Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 and sign in with `giulia.gaianet@gmail.com`.

---

## Step 7 — Verify access

Once logged in you should see:
- The ticket queue loading with data from BigQuery
- Your name and profile picture in the top left sidebar
- Filters working without errors

If you see a BigQuery permission error, make sure Step 4 completed successfully.

---

## Project structure

```
grant-helpdesk/
├── app.py                        # Streamlit dashboard (main UI)
├── bq_client.py                  # All BigQuery read/write functions
├── config.py                     # Table names, constants, domain lists
├── requirements.txt              # Python dependencies
├── .streamlit/
│   ├── config.toml               # Theme (light, Lesko brand colours)
│   └── secrets.toml              # OAuth credentials (not in git — see Step 5)
├── definitions/                  # Dataform SQLX pipeline
│   ├── marts/                    # Final tables (grant_tickets, grant_member_assignments)
│   ├── staging/                  # Staging models (stg_grant_posts, stg_team_engagement, ...)
│   ├── intelligence/             # AI classifier (grant_ticket_labels)
│   └── sources/                  # Source declarations
└── migrations/                   # One-off BQ SQL scripts (already run, for reference)
```

---

## Key BigQuery tables

| Table | Description |
|---|---|
| `grant_helpdesk.grant_tickets` | Main materialized ticket view (rebuilt by Dataform) |
| `grant_helpdesk.ticket_metadata` | Manual overrides — status, assignee, domain (written by the app) |
| `grant_helpdesk.member_assignment_overrides` | Permanent grant coach assignments per member |
| `grant_helpdesk.app_logs` | Error log from the app |

`grant_tickets` is rebuilt by Dataform. `ticket_metadata` is written directly by the app and live-joined at query time, so status/assignee changes show immediately without waiting for a Dataform run.

---

## Making pipeline changes (Dataform)

The Dataform repo is connected to GitHub. To make changes to the pipeline:

1. Edit the `.sqlx` files in `definitions/`
2. Commit and push to `main`
3. In the Dataform console (console.cloud.google.com → Dataform → grant-helpdesk), pull the latest changes into your workspace
4. Run the affected tables — use **Full Refresh** for incremental tables if you changed the schema

**Dataform details:**
- GCP project: `bigtribebuilders`
- Region: `europe-west1`
- Repository: `grant-helpdesk`
- Dataset: `grant_helpdesk`

---

## Brand colours

| Name   | Hex       | Used for                   |
|--------|-----------|----------------------------|
| Indigo | `#4a52a3` | Primary / sidebar / header |
| Yellow | `#f5c520` | Urgent tickets             |
| Green  | `#2e9b2e` | Answered / closed / normal |
| Blue   | `#2d6ee0` | Open tickets               |
| Red    | `#e03c3c` | Critical / cancelled       |

---

## Deploying to Cloud Run (future)

When deploying to Cloud Run, two things change:

1. In `.streamlit/secrets.toml`, update the redirect URI:
   ```toml
   redirect_uri = "https://your-cloud-run-url.run.app/oauth2callback"
   ```

2. In GCP Console → APIs & Services → Credentials → OAuth client, add the Cloud Run URL to **Authorized redirect URIs**.

Everything else (client ID, client secret, cookie secret) stays the same.

---

## Getting help

If something isn't working, ask Martin or open the issue in GitHub.
