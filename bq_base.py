"""
Shared BigQuery primitives: client handle, error logger, and schema-aware helpers.

This module is imported by bq_reads and bq_writes. It must not import from them
(one-directional dependency graph — see bq_client.py shim for re-exports).
"""

import uuid
import datetime
import sys
import time as _time

from google.cloud import bigquery

import config


try:
    client = bigquery.Client(project=config.PROJECT_ID)
except Exception as _e:
    print(
        "\n❌ Google Cloud credentials not found.\n"
        "Run the following commands and restart the app:\n\n"
        "    gcloud auth login\n"
        "    gcloud auth application-default login\n\n"
        "See ONBOARDING.md Step 4 for details.\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from _e


def log_event(level: str, source: str, message: str, detail: str = None):
    """Streaming-insert a log row into app_logs. Never raises — logging must not break the caller."""
    try:
        row = [{
            "log_id":     str(uuid.uuid4()),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "level":      level,
            "source":     source,
            "message":    message,
            "detail":     detail,
        }]
        client.insert_rows_json(config.LOGS_TABLE, row)
    except Exception:
        pass  # If BQ itself is down, nothing we can do here


# Cache tickets table schema with a 5-minute TTL. A one-shot module-load cache
# strands long-running containers with a stale schema view when Dataform rebuilds
# the table (a column added/removed in the mart was invisible to the running app
# until redeploy).
_TICKETS_COLS_CACHE: dict = {"cols": None, "expires_at": 0.0}
_TICKETS_COLS_TTL_SEC = 300


def _tickets_cols() -> set[str]:
    now = _time.time()
    cached = _TICKETS_COLS_CACHE["cols"]
    if cached is not None and _TICKETS_COLS_CACHE["expires_at"] > now:
        return cached
    try:
        cols = {f.name for f in client.get_table(config.TICKETS_TABLE).schema}
    except Exception as _e:
        log_event("WARNING", "bq_client._tickets_cols", "Could not refresh tickets table schema", str(_e))
        cols = cached if cached is not None else set()
    _TICKETS_COLS_CACHE["cols"] = cols
    _TICKETS_COLS_CACHE["expires_at"] = now + _TICKETS_COLS_TTL_SEC
    return cols


def _invalidate_tickets_cols() -> None:
    _TICKETS_COLS_CACHE["expires_at"] = 0.0


def _query_with_schema_retry(build_sql):
    """
    Run build_sql() → client.query → to_dataframe, with one retry on
    "Name X not found inside gt" errors. The retry forces _tickets_cols()
    to re-fetch from BigQuery before build_sql is called again, so SQL
    built around an optional column will adjust to the current schema.
    Used to survive transient mid-Dataform-rebuild races.
    """
    from google.api_core.exceptions import BadRequest
    try:
        return client.query(build_sql()).to_dataframe()
    except BadRequest as _e:
        if "not found inside" not in str(_e):
            raise
        log_event("WARNING", "bq_client._query_with_schema_retry",
                  "Schema/SQL mismatch — refreshing _tickets_cols and retrying", str(_e))
        _invalidate_tickets_cols()
        _tickets_cols()  # repopulate
        return client.query(build_sql()).to_dataframe()
