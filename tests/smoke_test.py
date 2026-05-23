"""
Smoke tests for the Grant Helpdesk app.

These run against real BigQuery — no mocks. They check that the most critical
functions work correctly before a deploy goes live. If any test fails, the
deploy script stops and nothing gets shipped.

Run manually:  cd grant-helpdesk && python3 -m pytest tests/smoke_test.py -v
Run via script: ./deploy.sh  (runs automatically before deploying)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import bq_client


# ── Read functions ─────────────────────────────────────────────────────────────

def test_get_open_stats_returns_expected_keys():
    """KPI numbers on the dashboard come from here — if it breaks, coaches see nothing."""
    stats = bq_client.get_open_stats()
    assert isinstance(stats, dict), "Expected a dict"
    for key in ("open", "normal", "urgent", "critical"):
        assert key in stats, f"Missing key: {key}"
        assert isinstance(stats[key], (int, float)), f"{key} should be a number"
        assert stats[key] >= 0, f"{key} should not be negative"


def test_get_tickets_returns_required_columns():
    """Ticket list must always have these columns — removing one breaks the UI."""
    df = bq_client.get_tickets(status="Open")
    assert isinstance(df, pd.DataFrame), "Expected a DataFrame"
    required = {"content_id", "ticket_status", "member_name", "created_at", "urgency"}
    missing = required - set(df.columns)
    assert not missing, f"Missing columns in get_tickets: {missing}"


def test_get_tickets_excludes_closed_by_default():
    """Default view must never show closed tickets to coaches."""
    df = bq_client.get_tickets(status="Open")
    if not df.empty:
        closed_rows = df[df["ticket_status"] == "closed"]
        assert closed_rows.empty, (
            f"get_tickets returned {len(closed_rows)} closed ticket(s) — "
            "should be excluded from default view"
        )


def test_get_app_logs_readable():
    """Error log must always be queryable — coaches depend on it for debugging."""
    df = bq_client.get_app_logs(limit=5)
    assert isinstance(df, pd.DataFrame)
    assert "level" in df.columns
    assert "source" in df.columns
    assert "message" in df.columns


def test_get_team_members_returns_list():
    """Assignee dropdown is populated from here."""
    members = bq_client.get_team_members()
    assert isinstance(members, list), "Expected a list"


# ── Write functions (SQL syntax validation) ────────────────────────────────────

def test_update_ticket_meta_answered_no_type_error():
    """
    Regression test for the NULL TIMESTAMP bug (caught 2026-05-20).
    When status != 'closed', closed_at must be CAST(NULL AS TIMESTAMP),
    not bare NULL — BigQuery can't infer the type of bare NULL in a MERGE.
    """
    try:
        bq_client.update_ticket_meta("_smoke_test_answered_", "answered", "")
    except Exception as e:
        err = str(e).lower()
        # A "not found" error means the SQL was valid but no row matched — that's fine.
        # Any other error (esp. "type" or "timestamp") means the SQL is broken.
        if "not found" in err or "no rows" in err:
            return  # SQL is valid
        raise AssertionError(f"update_ticket_meta raised unexpected error: {e}")


def test_update_ticket_meta_closed_no_type_error():
    """Same SQL path but with status='closed' — closed_at gets a real TIMESTAMP."""
    try:
        bq_client.update_ticket_meta(
            "_smoke_test_closed_", "closed", "", closed_by="smoke_test"
        )
    except Exception as e:
        err = str(e).lower()
        if "not found" in err or "no rows" in err:
            return
        raise AssertionError(f"update_ticket_meta (closed) raised unexpected error: {e}")


def test_get_followup_statuses_empty_input_returns_empty_dict():
    """Empty input must short-circuit without hitting BQ — no network call."""
    result = bq_client.get_followup_statuses([])
    assert result == {}, f"Expected empty dict, got {result}"


# ── Schema contract ────────────────────────────────────────────────────────────

def test_tickets_table_has_required_columns():
    """
    Dataform sometimes renames or drops columns. This catches schema drift
    before it silently breaks queries in bq_client.py.
    """
    required = {
        "content_id", "ticket_status", "member_id", "member_name",
        "created_at", "body", "thread_id", "content_type",
    }
    missing = required - bq_client._tickets_cols()
    assert not missing, (
        f"grant_tickets is missing expected columns: {missing}\n"
        "Run Dataform to rebuild, or check if a column was renamed."
    )
