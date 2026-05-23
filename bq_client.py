"""
bq_client — thin re-export shim.

The original 1280-line module was split into:
  - bq_base   : client, log_event, schema-aware helpers
  - bq_reads  : SELECT queries
  - bq_writes : INSERT / MERGE / UPDATE / DELETE
  - mn_api    : Mighty Networks REST calls

Callers (`app.py`, `tests/smoke_test.py`) continue to use `import bq_client`
and `bq_client.func(...)` exactly as before. This module re-exports every
public symbol so call sites don't need to change.
"""

from bq_base import *      # noqa: F401,F403  — client, log_event
from bq_reads import *     # noqa: F401,F403  — get_*, search_members, preview_bulk_close
from bq_writes import *    # noqa: F401,F403  — TEAM_FEEDBACK_TABLE, post_*, update_*, etc.
from mn_api import *       # noqa: F401,F403  — mn_promote_to_host, rsvp_*, delete_mn_post, post_mn_comment

# Underscored helpers — `from X import *` skips leading-underscore names, so
# re-export them explicitly. tests/smoke_test.py calls bq_client._tickets_cols().
from bq_base import (      # noqa: F401
    _tickets_cols,
    _invalidate_tickets_cols,
    _query_with_schema_retry,
)
from bq_reads import _live_status_cte  # noqa: F401
