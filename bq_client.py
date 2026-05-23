import uuid
import datetime
import traceback
import pandas as pd
from google.cloud import bigquery
import config

try:
    client = bigquery.Client(project=config.PROJECT_ID)
except Exception as _e:
    import sys
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


import time as _time

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


def get_unreviewed_rejects(days: int = 1) -> pd.DataFrame:
    """Posts/articles/comments the classifier rejected and the team hasn't reviewed yet."""
    sql = f"""
        SELECT *
        FROM `{config.TICKETS_TABLE}`
        WHERE ticket_status = 'not_a_question'
          AND manual_status IS NULL
          AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(days)} DAY)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY created_at DESC) = 1
        ORDER BY created_at DESC
    """
    return client.query(sql).to_dataframe()


def get_team_members() -> list[str]:
    sql = f"""
        SELECT full_name
        FROM `{config.GRANT_COACHES_TABLE}`
        ORDER BY full_name
    """
    rows = client.query(sql).to_dataframe()
    return rows["full_name"].tolist()


def get_tickets(
    status=None,
    date_from=None,
    date_to=None,
    assignee=None,
    member_id=None,
    urgency=None,

    domain=None,
) -> pd.DataFrame:
    filters = ["body IS NOT NULL AND TRIM(body) != ''"]

    if status and status != "All":
        filters.append(f"ticket_status = '{status}'")
    else:
        # Feedback statuses are hidden from the default view
        filters.append(f"ticket_status NOT IN ('not_a_question', 'confirmed_question', 'closed')")
    if assignee and assignee != "All":
        filters.append(f"assigned_to = '{assignee}'")
    if member_id:
        filters.append(f"CAST(member_id AS STRING) = '{member_id}'")

    if domain and domain != "All":
        filters.append(f"domain = '{domain}'")
    if date_from:
        filters.append(f"DATE(created_at) >= '{date_from}'")
    if date_to:
        filters.append(f"DATE(created_at) <= '{date_to}'")

    # Urgency maps directly to age conditions
    urgency_conditions = {
        "Normal":   "TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24",
        "Urgent":   "TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) BETWEEN 24 AND 47",
        "Critical": "TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) >= 48",
    }
    if urgency and urgency != "All" and urgency in urgency_conditions:
        filters.append(urgency_conditions[urgency])

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    def _build():
        # Build EXCEPT and CASE clauses based on what columns actually exist in
        # the table. Run inside _query_with_schema_retry so a mid-Dataform-
        # rebuild schema mismatch refreshes _tickets_cols() and tries again.
        _gt_cols = _tickets_cols()
        _always_except = ["assigned_to", "manual_status", "domain", "ticket_status"]
        _optional_except = ["difficulty", "team_comment_replied"]
        _except_cols = ", ".join(_always_except + [c for c in _optional_except if c in _gt_cols])
        _reopen_clause = (
            "WHEN tm.status = 'closed' AND gt.last_member_activity_at IS NOT NULL "
            "AND tm.closed_at IS NOT NULL AND gt.last_member_activity_at > tm.closed_at THEN 'open'"
        ) if "last_member_activity_at" in _gt_cols else ""
        return f"""
            WITH live AS (
                SELECT
                    gt.* EXCEPT({_except_cols}),
                    COALESCE(tm.assigned_to, gt.assigned_to)               AS assigned_to,
                    tm.status                                               AS manual_status,
                    COALESCE(tm.domain, gt.domain)                          AS domain,
                    CASE
                        {_reopen_clause}
                        WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                        ELSE gt.ticket_status
                    END                                                     AS ticket_status
                FROM `{config.TICKETS_TABLE}` gt
                LEFT JOIN (
                    SELECT * FROM `{config.META_TABLE}`
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
                ) tm ON gt.content_id = tm.content_id
                QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
            )
            SELECT
                *,
                LEFT(body, 600) AS body_preview,
                CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24 THEN 'normal'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 48 THEN 'urgent'
                    ELSE 'critical'
                END AS urgency
            FROM live
            {where}
            ORDER BY created_at DESC
        """
    df = _query_with_schema_retry(_build)
    if "domain" not in df.columns:
        df["domain"] = None
    return df


def get_ticket_detail(content_id: str) -> dict:
    def _build():
        _gt_cols = _tickets_cols()
        _always_except = ["assigned_to", "manual_status", "domain", "ticket_status"]
        _optional_except = ["difficulty", "team_comment_replied"]
        _except_cols = ", ".join(_always_except + [c for c in _optional_except if c in _gt_cols])
        _reopen_clause = (
            "WHEN tm.status = 'closed' AND gt.last_member_activity_at IS NOT NULL "
            "AND tm.closed_at IS NOT NULL AND gt.last_member_activity_at > tm.closed_at THEN 'open'"
        ) if "last_member_activity_at" in _gt_cols else ""
        return f"""
            SELECT
                gt.* EXCEPT({_except_cols}),
                COALESCE(tm.assigned_to, gt.assigned_to)               AS assigned_to,
                tm.status                                               AS manual_status,
                COALESCE(tm.domain, gt.domain)                          AS domain,
                CASE
                    {_reopen_clause}
                    WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                    ELSE gt.ticket_status
                END                                                     AS ticket_status,
                CASE
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), gt.created_at, HOUR) < 24 THEN 'normal'
                    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), gt.created_at, HOUR) < 48 THEN 'urgent'
                    ELSE 'critical'
                END AS urgency
            FROM `{config.TICKETS_TABLE}` gt
            LEFT JOIN (
                SELECT * FROM `{config.META_TABLE}`
                QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
            ) tm ON gt.content_id = tm.content_id
            WHERE gt.content_id = '{content_id}'
            LIMIT 1
        """
    df = _query_with_schema_retry(_build)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def get_member_thread_tickets(thread_id: str, member_id) -> pd.DataFrame:
    """All tickets from one member in one thread (all statuses), used by the group dialog."""
    def _build():
        _gt_cols = _tickets_cols()
        _always_except = ["assigned_to", "manual_status", "domain", "ticket_status"]
        _optional_except = ["difficulty", "team_comment_replied"]
        _except_cols = ", ".join(_always_except + [c for c in _optional_except if c in _gt_cols])
        _reopen_clause = (
            "WHEN tm.status = 'closed' AND gt.last_member_activity_at IS NOT NULL "
            "AND tm.closed_at IS NOT NULL AND gt.last_member_activity_at > tm.closed_at THEN 'open'"
        ) if "last_member_activity_at" in _gt_cols else ""
        return f"""
            WITH live AS (
                SELECT
                    gt.* EXCEPT({_except_cols}),
                    COALESCE(tm.assigned_to, gt.assigned_to)               AS assigned_to,
                    tm.status                                               AS manual_status,
                    COALESCE(tm.domain, gt.domain)                         AS domain,
                    CASE
                        {_reopen_clause}
                        WHEN tm.status IS NOT NULL AND tm.status != ''     THEN tm.status
                        ELSE gt.ticket_status
                    END                                                    AS ticket_status,
                    CASE
                        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), gt.created_at, HOUR) < 24 THEN 'normal'
                        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), gt.created_at, HOUR) < 48 THEN 'urgent'
                        ELSE 'critical'
                    END AS urgency
                FROM `{config.TICKETS_TABLE}` gt
                LEFT JOIN (
                    SELECT * FROM `{config.META_TABLE}`
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
                ) tm ON gt.content_id = tm.content_id
                WHERE gt.thread_id = '{thread_id}'
                  AND CAST(gt.member_id AS STRING) = '{member_id}'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
            )
            SELECT *, LEFT(body, 300) AS body_preview
            FROM live
            ORDER BY created_at ASC
        """
    df = _query_with_schema_retry(_build)
    if "domain" not in df.columns:
        df["domain"] = None
    return df


def get_comments(content_id: str) -> pd.DataFrame:
    sql = f"""
        SELECT comment_id, author, body, created_at
        FROM `{config.COMMENTS_VIEW}`
        WHERE content_id = '{content_id}'
        ORDER BY created_at ASC
    """
    return client.query(sql).to_dataframe()


def post_comment(content_id: str, author: str, body: str):
    table = client.get_table(config.COMMENTS_TABLE)
    row = [{
        "comment_id": str(uuid.uuid4()),
        "content_id": content_id,
        "author":     author,
        "body":       body,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }]
    errors = client.insert_rows_json(table, row)
    if errors:
        raise RuntimeError(f"Comment insert failed: {errors}")


def get_mn_api_key(email: str) -> str | None:
    """Return the stored Mighty Networks API key for a user, or None."""
    sql = f"""
        SELECT mn_api_key
        FROM `{config.TEAM_API_KEYS_TABLE}`
        WHERE email = '{email}'
        ORDER BY updated_at DESC
        LIMIT 1
    """
    df = client.query(sql).to_dataframe()
    if df.empty:
        return None
    return df.iloc[0]["mn_api_key"]


def save_mn_api_key(email: str, api_key: str):
    """Upsert a Mighty Networks API key for a user."""
    sql = f"""
        MERGE `{config.TEAM_API_KEYS_TABLE}` T
        USING (SELECT '{email}' AS email, '{api_key}' AS mn_api_key) S
        ON T.email = S.email
        WHEN MATCHED THEN
            UPDATE SET mn_api_key = S.mn_api_key, updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT (email, mn_api_key, updated_at)
            VALUES (S.email, S.mn_api_key, CURRENT_TIMESTAMP())
    """
    client.query(sql).result()


def search_members(query: str, limit: int = 20) -> pd.DataFrame:
    """Search community members by name or email.
    Pass query='' to load all active members (used for in-memory search cache)."""
    q = (query or "").strip()
    params = [bigquery.ScalarQueryParameter("limit", "INT64", int(limit))]
    where_search = ""
    if q:
        where_search = """AND (
              LOWER(CONCAT(COALESCE(m.first_name,''), ' ', COALESCE(m.last_name,''))) LIKE @pattern
              OR LOWER(m.email_address) LIKE @pattern
          )"""
        params.append(
            bigquery.ScalarQueryParameter("pattern", "STRING", f"%{q.lower()}%")
        )
    sql = f"""
        SELECT
            m.member_id,
            TRIM(CONCAT(COALESCE(m.first_name,''), ' ', COALESCE(m.last_name,''))) AS full_name,
            m.email_address,
            m.network_role,
            m.join_date
        FROM `{config.PROJECT_ID}.dataform.core_members` m
        WHERE m.client_id = 'lesko_4022250'
          AND LOWER(m.member_status) = 'active'
          {where_search}
        ORDER BY m.last_name, m.first_name
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    return client.query(sql, job_config=job_config).to_dataframe()


def get_grant_coaches() -> pd.DataFrame:
    sql = f"""
        SELECT gc.member_id, gc.full_name, gc.email, gc.login_email, gc.added_at, gc.added_by
        FROM `{config.GRANT_COACHES_TABLE}` gc
        ORDER BY gc.added_at DESC
    """
    return client.query(sql).to_dataframe()


def get_coach_by_login_email(login_email: str):
    """Return the coach row for a given login email (checks both login_email and MN email)."""
    e = login_email.replace("'", "\\'")
    sql = f"""
        SELECT member_id, full_name, email, login_email
        FROM `{config.GRANT_COACHES_TABLE}`
        WHERE login_email = '{e}' OR email = '{e}'
        LIMIT 1
    """
    df = client.query(sql).to_dataframe()
    return df.iloc[0].to_dict() if not df.empty else None


def link_coach_login_email(member_id: int, login_email: str):
    """Save the portal login email for a coach so future logins are recognised."""
    e = login_email.replace("'", "\\'")
    sql = f"""
        UPDATE `{config.GRANT_COACHES_TABLE}`
        SET login_email = '{e}'
        WHERE member_id = {member_id}
    """
    client.query(sql).result()


def get_unlinked_coaches() -> pd.DataFrame:
    """Coaches that haven't linked a portal login yet (login_email is NULL)."""
    sql = f"""
        SELECT member_id, full_name, email
        FROM `{config.GRANT_COACHES_TABLE}`
        WHERE login_email IS NULL OR login_email = ''
        ORDER BY full_name
    """
    return client.query(sql).to_dataframe()


def add_grant_coach(member_id: int, full_name: str, email: str, added_by: str):
    now = datetime.datetime.utcnow().isoformat()
    _name     = full_name.replace("'", "\\'")
    _email    = email.replace("'", "\\'")
    _added_by = added_by.replace("'", "\\'")
    sql = f"""
        INSERT INTO `{config.GRANT_COACHES_TABLE}` (member_id, full_name, email, added_at, added_by)
        VALUES ({member_id}, '{_name}', '{_email}', TIMESTAMP '{now}', '{_added_by}')
    """
    client.query(sql).result()


def remove_grant_coach(member_id: int):
    sql = f"""
        DELETE FROM `{config.GRANT_COACHES_TABLE}`
        WHERE member_id = {member_id}
    """
    client.query(sql).result()


def mn_promote_to_host(member_id: int, admin_api_key: str) -> dict:
    """Promote a community member to host role via MN Admin API."""
    import requests as _requests
    url = f"{config.MN_API_BASE}/networks/{config.MN_NETWORK_ID}/members/{member_id}"
    headers = {
        "Authorization": f"Bearer {admin_api_key.strip()}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "User-Agent":    "mn-api-client/1.0",
    }
    response = _requests.patch(url, headers=headers, json={"role": "host"}, timeout=30)
    if response.status_code in (200, 201, 204):
        return response.json() if response.content else {}
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise RuntimeError(f"HTTP {response.status_code} — {detail}")


def get_upcoming_events() -> list[dict]:
    """Return upcoming RSVP-enabled events from BQ, ordered by start time."""
    sql = f"""
        SELECT event_id, title, starts_at, ends_at, time_zone,
               event_type, zoom_link, permalink
        FROM `{config.PROJECT_ID}.grant_helpdesk.upcoming_events`
        WHERE starts_at > CURRENT_TIMESTAMP()
        ORDER BY starts_at ASC
    """
    df = client.query(sql).to_dataframe()
    return df.to_dict("records")


def rsvp_member_to_event(event_id: int, member_id: str, api_key: str) -> None:
    """RSVP a member to a Mighty Networks event via the Admin API."""
    import requests as _requests
    url = f"{config.MN_API_BASE}/networks/{config.MN_NETWORK_ID}/events/{event_id}/rsvps"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "User-Agent":    "mn-api-client/1.0",
    }
    response = _requests.post(url, headers=headers, json={"member_id": int(member_id), "status": "going"}, timeout=30)
    if response.status_code in (200, 201, 204):
        return
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise RuntimeError(f"HTTP {response.status_code} — {detail}")


def log_rsvp(content_id: str, event_id: int, member_id: str, rsvped_by: str) -> None:
    """Log an RSVP action to BQ."""
    row = [{
        "id":         str(uuid.uuid4()),
        "content_id": content_id,
        "event_id":   event_id,
        "member_id":  str(member_id),
        "rsvped_by":  rsvped_by or "",
        "rsvped_at":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }]
    errors = client.insert_rows_json(f"{config.PROJECT_ID}.grant_helpdesk.rsvp_log", row)
    if errors:
        raise RuntimeError(f"BQ log error: {errors}")


def delete_mn_post(post_id: str, api_key: str) -> None:
    """Delete a post from Mighty Networks via the Admin API."""
    import requests as _requests
    # content_id from BQ has the form "<type>_<numeric>" (e.g. "post_102202964").
    # MN's URL expects just the numeric part.
    _, _, _num = str(post_id).rpartition("_")
    _numeric = _num or str(post_id)
    url = f"{config.MN_API_BASE}/networks/{config.MN_NETWORK_ID}/posts/{int(_numeric)}"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept":        "application/json",
        "User-Agent":    "mn-api-client/1.0",
    }
    response = _requests.delete(url, headers=headers, timeout=30)
    if response.status_code in (200, 204):
        return
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise RuntimeError(f"HTTP {response.status_code} — {detail}")


def post_mn_comment(post_id: str, body: str, api_key: str, reply_to_id: int = None) -> dict:
    """Post a comment to Mighty Networks via the API. Returns the created comment dict."""
    import requests as _requests
    url = f"{config.MN_API_BASE}/networks/{config.MN_NETWORK_ID}/posts/{int(post_id)}/comments"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "User-Agent":    "mn-api-client/1.0",
    }
    payload = {"text": body}
    if reply_to_id is not None:
        payload["reply_to_id"] = int(reply_to_id)
    response = _requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 201:
        return response.json()
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise RuntimeError(f"HTTP {response.status_code} — {detail}")


def queue_followup(
    ticket_id: str,
    content_id: str,
    content_type: str,
    member_id: str,
    member_name: str,
    message: str,
    days: int,
    scheduled_by: str,
) -> None:
    """Insert a pending follow-up into the followup_queue table."""
    now = datetime.datetime.utcnow()
    send_after = now + datetime.timedelta(days=int(days))
    row = [{
        "id":            str(uuid.uuid4()),
        "ticket_id":     ticket_id,
        "content_id":    content_id,
        "content_type":  content_type,
        "member_id":     str(member_id) if member_id else "",
        "member_name":   member_name or "",
        "message":       message,
        "send_after":    send_after.isoformat(),
        "status":        "pending",
        "scheduled_by":  scheduled_by,
        "created_at":    now.isoformat(),
    }]
    errors = client.insert_rows_json(config.FOLLOWUP_QUEUE_TABLE, row)
    if errors:
        raise RuntimeError(f"BQ insert errors: {errors}")


def get_followup_statuses(content_ids: list) -> dict:
    """Return {ticket_id: {status, send_after, sent_at}} for any tickets with a follow-up queued."""
    if not content_ids:
        return {}
    ids_str = ", ".join(f"'{c}'" for c in content_ids)
    sql = f"""
        SELECT ticket_id, status, send_after, sent_at
        FROM `{config.FOLLOWUP_QUEUE_TABLE}`
        WHERE ticket_id IN ({ids_str})
        QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY created_at DESC) = 1
    """
    try:
        df = client.query(sql).to_dataframe()
        return {str(r["ticket_id"]): r.to_dict() for _, r in df.iterrows()}
    except Exception as e:
        log_event("ERROR", "bq_client.get_followup_statuses", str(e))
        return {}


def update_followup_status(followup_id: str, status: str, **kwargs) -> None:
    """Update a followup_queue row. kwargs: sent_at, skipped_at, skipped_reason."""
    sets = [f"status = '{status}'"]
    if "sent_at" in kwargs:
        sets.append(f"sent_at = TIMESTAMP '{kwargs['sent_at']}'")
    if "skipped_at" in kwargs:
        sets.append(f"skipped_at = TIMESTAMP '{kwargs['skipped_at']}'")
    if "skipped_reason" in kwargs:
        reason = (kwargs["skipped_reason"] or "").replace("'", "\\'")
        sets.append(f"skipped_reason = '{reason}'")
    sql = f"""
        UPDATE `{config.FOLLOWUP_QUEUE_TABLE}`
        SET {', '.join(sets)}
        WHERE id = '{followup_id}'
    """
    client.query(sql).result()


def preview_bulk_close(
    status_filter: str = "answered",
    assigned_to: str = "",
    before_date: str = "",
) -> dict:
    """
    Returns {"will_close": N, "skipped_followup": M} for the given filters.
    Excludes already-closed/cancelled tickets and those with pending follow-ups.
    """
    conditions = ["t.effective_status NOT IN ('closed', 'cancelled')"]
    if status_filter:
        safe_status = status_filter.replace("'", "")
        conditions.append(f"t.effective_status = '{safe_status}'")
    if assigned_to:
        safe_assigned = assigned_to.replace("'", "\\'")
        conditions.append(f"t.effective_assigned_to = '{safe_assigned}'")
    if before_date:
        safe_date = before_date.replace("'", "")
        conditions.append(f"DATE(t.created_at) < '{safe_date}'")

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        WITH base AS (
            SELECT
                gt.content_id,
                gt.created_at,
                CASE
                    WHEN tm.status IS NOT NULL AND tm.status != '' THEN tm.status
                    ELSE gt.ticket_status
                END AS effective_status,
                COALESCE(tm.assigned_to, gt.assigned_to) AS effective_assigned_to
            FROM `{config.TICKETS_TABLE}` gt
            LEFT JOIN (
                SELECT * FROM `{config.META_TABLE}`
                QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
            ) tm ON gt.content_id = tm.content_id
            QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
        ),
        filtered AS (
            SELECT t.content_id
            FROM base t
            {where}
        )
        SELECT
            COUNT(*) AS total,
            COUNTIF(fq.ticket_id IS NOT NULL) AS skipped_followup
        FROM filtered f
        LEFT JOIN (
            SELECT DISTINCT ticket_id
            FROM `{config.FOLLOWUP_QUEUE_TABLE}`
            WHERE status = 'pending'
        ) fq ON f.content_id = fq.ticket_id
    """
    row = list(client.query(sql).result())[0]
    total        = int(row["total"])
    skipped      = int(row["skipped_followup"])
    return {"will_close": total - skipped, "skipped_followup": skipped}


def execute_bulk_close(
    status_filter: str = "answered",
    assigned_to: str = "",
    before_date: str = "",
    closed_by: str = "",
) -> int:
    """
    Closes all matching tickets, skipping those with pending follow-ups.
    Returns the number of tickets closed.
    """
    now = datetime.datetime.utcnow().isoformat()
    closed_by_val = (closed_by or "").replace("'", "\\'")

    conditions = ["t.effective_status NOT IN ('closed', 'cancelled')"]
    if status_filter:
        safe_status = status_filter.replace("'", "")
        conditions.append(f"t.effective_status = '{safe_status}'")
    if assigned_to:
        safe_assigned = assigned_to.replace("'", "\\'")
        conditions.append(f"t.effective_assigned_to = '{safe_assigned}'")
    if before_date:
        safe_date = before_date.replace("'", "")
        conditions.append(f"DATE(t.created_at) < '{safe_date}'")

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        MERGE `{config.META_TABLE}` T
        USING (
            WITH base AS (
                SELECT
                    gt.content_id,
                    gt.created_at,
                    COALESCE(tm.assigned_to, gt.assigned_to) AS assigned_to,
                    COALESCE(tm.domain, gt.domain)           AS domain,
                    CASE
                        WHEN tm.status IS NOT NULL AND tm.status != '' THEN tm.status
                        ELSE gt.ticket_status
                    END AS effective_status,
                    COALESCE(tm.assigned_to, gt.assigned_to) AS effective_assigned_to
                FROM `{config.TICKETS_TABLE}` gt
                LEFT JOIN (
                    SELECT * FROM `{config.META_TABLE}`
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
                ) tm ON gt.content_id = tm.content_id
                QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
            )
            SELECT t.content_id, t.assigned_to, t.domain
            FROM base t
            {where}
            AND t.content_id NOT IN (
                SELECT DISTINCT ticket_id
                FROM `{config.FOLLOWUP_QUEUE_TABLE}`
                WHERE status = 'pending'
            )
        ) S
        ON T.content_id = S.content_id
        WHEN MATCHED THEN UPDATE SET
            status     = 'closed',
            updated_at = TIMESTAMP '{now}',
            closed_at  = TIMESTAMP '{now}',
            closed_by  = '{closed_by_val}'
        WHEN NOT MATCHED THEN INSERT
            (content_id, status, assigned_to, domain, updated_at, closed_at, closed_by)
        VALUES
            (S.content_id, 'closed', S.assigned_to, S.domain,
             TIMESTAMP '{now}', TIMESTAMP '{now}', '{closed_by_val}')
    """
    job = client.query(sql)
    job.result()
    return job.num_dml_affected_rows or 0


def update_ticket_meta(
    content_id: str,
    status: str,
    assigned_to: str,
    domain: str = None,
    feedback_reason: str = None,
    closed_by: str = None,
):
    now        = datetime.datetime.utcnow().isoformat()
    domain_val = domain or ""
    reason_val = (feedback_reason or "").replace("'", "\\'")
    closed_by_val = (closed_by or "").replace("'", "\\'")
    # Write closed_at timestamp when closing; clear it when reopening or changing status.
    # CAST(NULL AS ...) is required — bare NULL in a MERGE USING clause has no type in BigQuery.
    closed_at_sql = f"TIMESTAMP '{now}'" if status == "closed" else "CAST(NULL AS TIMESTAMP)"
    closed_by_sql = f"'{closed_by_val}'" if status == "closed" and closed_by_val else "CAST(NULL AS STRING)"
    sql = f"""
        MERGE `{config.META_TABLE}` T
        USING (
            SELECT
                '{content_id}'     AS content_id,
                '{status}'         AS status,
                '{assigned_to}'    AS assigned_to,
                '{domain_val}'     AS domain,
                '{reason_val}'     AS feedback_reason,
                TIMESTAMP '{now}'  AS updated_at,
                {closed_at_sql}    AS closed_at,
                {closed_by_sql}    AS closed_by
        ) S
        ON T.content_id = S.content_id
        WHEN MATCHED THEN UPDATE SET
            status          = S.status,
            assigned_to     = S.assigned_to,
            domain          = S.domain,
            feedback_reason = S.feedback_reason,
            updated_at      = S.updated_at,
            closed_at       = S.closed_at,
            closed_by       = S.closed_by
        WHEN NOT MATCHED THEN INSERT
            (content_id, status, assigned_to, domain, feedback_reason, updated_at, closed_at, closed_by)
        VALUES
            (S.content_id, S.status, S.assigned_to, S.domain, S.feedback_reason, S.updated_at, S.closed_at, S.closed_by)
    """
    client.query(sql).result()
    if assigned_to:
        trigger_assignment_refresh()


def trigger_assignment_refresh():
    """
    Fire a Dataform workflow invocation to rebuild grant_member_assignments
    and grant_tickets after an assignment changes. Fire-and-forget — Dataform
    runs the rebuild asynchronously. Errors are swallowed so the save flow is
    never broken.
    """
    try:
        from google.cloud import dataform_v1beta1

        df_client = dataform_v1beta1.DataformClient()
        repo = (
            f"projects/{config.PROJECT_ID}"
            f"/locations/{config.DATAFORM_REGION}"
            f"/repositories/{config.DATAFORM_REPOSITORY}"
        )

        # Use the most recent compilation result so we don't need to compile fresh.
        req = dataform_v1beta1.ListCompilationResultsRequest(parent=repo)
        results = list(df_client.list_compilation_results(request=req))
        if not results:
            return

        invocation = dataform_v1beta1.WorkflowInvocation(
            compilation_result=results[0].name,
            invocation_config=dataform_v1beta1.InvocationConfig(
                included_targets=[
                    dataform_v1beta1.Target(
                        database=config.PROJECT_ID,
                        schema=config.DATASET,
                        name="grant_member_assignments",
                    ),
                    dataform_v1beta1.Target(
                        database=config.PROJECT_ID,
                        schema=config.DATASET,
                        name="grant_tickets",
                    ),
                ],
                # Don't re-run upstream sources — ticket_metadata was just
                # written by the app and grant_content is already materialized.
                transitive_dependencies_included=False,
                transitive_dependents_included=False,
            ),
        )
        df_client.create_workflow_invocation(
            parent=repo, workflow_invocation=invocation
        )
    except Exception as e:
        log_event(
            level="ERROR",
            source="trigger_assignment_refresh",
            message=str(e),
            detail=traceback.format_exc(),
        )


def set_ticket_assignee(content_id: str, assigned_to: str):
    """Update only the assigned_to field on a ticket without touching any other metadata."""
    now = datetime.datetime.utcnow().isoformat()
    sql = f"""
        MERGE `{config.META_TABLE}` T
        USING (
            SELECT
                '{content_id}'    AS content_id,
                '{assigned_to}'   AS assigned_to,
                TIMESTAMP '{now}' AS updated_at
        ) S
        ON T.content_id = S.content_id
        WHEN MATCHED THEN UPDATE SET
            assigned_to = S.assigned_to,
            updated_at  = S.updated_at
        WHEN NOT MATCHED THEN INSERT
            (content_id, assigned_to, updated_at)
        VALUES
            (S.content_id, S.assigned_to, S.updated_at)
    """
    client.query(sql).result()
    trigger_assignment_refresh()


def set_member_assignment_override(member_id: int, assigned_to: str, updated_by: str):
    now = datetime.datetime.utcnow().isoformat()
    sql = f"""
        MERGE `{config.MEMBER_ASSIGNMENTS_TABLE}` T
        USING (
            SELECT
                {member_id}        AS member_id,
                '{assigned_to}'    AS assigned_to,
                TIMESTAMP '{now}'  AS updated_at,
                '{updated_by}'     AS updated_by
        ) S
        ON T.member_id = S.member_id
        WHEN MATCHED THEN UPDATE SET
            assigned_to = S.assigned_to,
            updated_at  = S.updated_at,
            updated_by  = S.updated_by
        WHEN NOT MATCHED THEN INSERT
            (member_id, assigned_to, updated_at, updated_by)
        VALUES
            (S.member_id, S.assigned_to, S.updated_at, S.updated_by)
    """
    client.query(sql).result()
    trigger_assignment_refresh()


def get_prompt_history() -> pd.DataFrame:
    """
    Returns all prompt versions with their classifier stats and feedback counts.
    Each row covers the period from that version's created_at until the next
    version's created_at (or NOW for the current version).
    """
    sql = f"""
        WITH
          versions AS (
            SELECT
              version,
              prompt_text,
              change_reason,
              created_by,
              created_at,
              LEAD(created_at) OVER (ORDER BY version) AS superseded_at
            FROM `{config.PROMPT_CONFIG_TABLE}`
          ),
          classifier_stats AS (
            SELECT
              v.version,
              COUNT(*)                        AS total_classified,
              COUNTIF(qc.is_question = TRUE)  AS classified_as_question
            FROM versions v
            LEFT JOIN `{config.CLASSIFIER_TABLE}` qc
              ON  qc.classified_at >= v.created_at
              AND (v.superseded_at IS NULL OR qc.classified_at < v.superseded_at)
            GROUP BY v.version
          ),
          feedback_stats AS (
            SELECT
              v.version,
              COUNTIF(f.feedback_type = 'not_a_question')     AS false_positives,
              COUNTIF(f.feedback_type = 'confirmed_question')  AS confirmed_questions
            FROM versions v
            LEFT JOIN `{config.FEEDBACK_VIEW}` f
              ON  f.flagged_at >= v.created_at
              AND (v.superseded_at IS NULL OR f.flagged_at < v.superseded_at)
            GROUP BY v.version
          )
        SELECT
          v.version,
          v.prompt_text,
          v.change_reason,
          v.created_at,
          v.superseded_at,
          (v.superseded_at IS NULL)                      AS is_current,
          COALESCE(cs.total_classified,    0)            AS total_classified,
          COALESCE(cs.classified_as_question, 0)         AS classified_as_question,
          COALESCE(fs.false_positives,     0)            AS false_positives,
          COALESCE(fs.confirmed_questions, 0)            AS confirmed_questions
        FROM versions v
        LEFT JOIN classifier_stats cs ON cs.version = v.version
        LEFT JOIN feedback_stats   fs ON fs.version = v.version
        ORDER BY v.version DESC
    """
    return client.query(sql).to_dataframe()


def get_classification_feedback(date_from: str, date_to: str) -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM `{config.FEEDBACK_VIEW}`
        WHERE DATE(flagged_at) BETWEEN '{date_from}' AND '{date_to}'
        ORDER BY flagged_at DESC
    """
    return client.query(sql).to_dataframe()


def _live_status_cte() -> str:
    """
    Returns the reopen_clause string for building the live-join CTE status CASE.
    Used by both get_open_stats() and get_daily_stats() so their KPI numbers
    always match the ticket list (which also uses a live join).
    """
    _gt_cols = _tickets_cols()
    return (
        "WHEN tm.status = 'closed' AND gt.last_member_activity_at IS NOT NULL "
        "AND tm.closed_at IS NOT NULL AND gt.last_member_activity_at > tm.closed_at THEN 'open'"
    ) if "last_member_activity_at" in _gt_cols else ""


def get_open_stats() -> dict:
    def _build():
        _reopen_clause = _live_status_cte()
        return f"""
            WITH live AS (
                SELECT
                    gt.created_at,
                    CASE
                        {_reopen_clause}
                        WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                        ELSE gt.ticket_status
                    END AS ticket_status
                FROM `{config.TICKETS_TABLE}` gt
                LEFT JOIN (
                    SELECT * FROM `{config.META_TABLE}`
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
                ) tm ON gt.content_id = tm.content_id
                QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
            )
            SELECT
                COUNTIF(ticket_status IN ('open', 'new', 'assigned'))                                       AS open,
                COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                    AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24)                         AS normal,
                COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                    AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) BETWEEN 24 AND 47)            AS urgent,
                COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                    AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) >= 48)                        AS critical
            FROM live
        """
    row = _query_with_schema_retry(_build).iloc[0]
    return row.to_dict()


def get_daily_stats() -> dict:
    def _build():
        _reopen_clause = _live_status_cte()
        return f"""
            WITH live AS (
                SELECT
                    gt.created_at,
                    gt.first_engagement_at,
                    COALESCE(tm.updated_at, gt.ticket_updated_at) AS ticket_updated_at,
                    CASE
                        {_reopen_clause}
                        WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                        ELSE gt.ticket_status
                    END AS ticket_status
                FROM `{config.TICKETS_TABLE}` gt
                LEFT JOIN (
                    SELECT * FROM `{config.META_TABLE}`
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
                ) tm ON gt.content_id = tm.content_id
                QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
            )
            SELECT
                COUNTIF(DATE(created_at) = CURRENT_DATE())                                              AS in_today,
                COUNTIF(ticket_status IN ('answered', 'closed')
                    AND DATE(COALESCE(first_engagement_at, ticket_updated_at)) = CURRENT_DATE())        AS answered_today,
                ROUND(
                    COUNTIF(
                        ticket_status IN ('answered', 'closed')
                        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                    ) / 30.0, 1
                )                                                                                       AS daily_avg
            FROM live
        """
    row = _query_with_schema_retry(_build).iloc[0]
    result = row.to_dict()
    result["goal"] = config.DAILY_GOAL
    return result


def get_thread(thread_id: str) -> pd.DataFrame:
    """
    Fetch every item in a thread — root post + all comments — ordered by time.
    thread_id is always 'post_NNN'. Returns author_type ('team'/'member') and
    depth so the UI can render the conversation correctly.
    """
    if thread_id.startswith("comment_"):
        # thread_id not yet backfilled — look up the parent post from core_comments
        comment_id = thread_id.replace("comment_", "")
        lookup = client.query(f"""
            SELECT CAST(targetable_id AS STRING) AS post_id
            FROM `bigtribebuilders.dataform.core_comments`
            WHERE comment_id = {comment_id} AND client_id = 'lesko_4022250'
            LIMIT 1
        """).to_dataframe()
        if lookup.empty:
            return pd.DataFrame()
        post_id = lookup.iloc[0]["post_id"]
    else:
        post_id = thread_id.replace("post_", "")
    sql = f"""
        WITH root_post AS (
            SELECT
                CONCAT('post_', CAST(p.post_id AS STRING))   AS content_id,
                'post'                                         AS content_type,
                0                                              AS depth,
                CAST(NULL AS INT64)                            AS reply_to_id,
                p.creator_id                                   AS author_id,
                TRIM(CONCAT(
                    COALESCE(m.first_name, ''), ' ',
                    COALESCE(m.last_name,  '')
                ))                                             AS author_name,
                CASE
                    WHEN m.network_role IN ('host', 'moderator') THEN 'team'
                    ELSE 'member'
                END                                            AS author_type,
                TRIM(REGEXP_REPLACE(
                    REGEXP_REPLACE(COALESCE(p.description, ''), r'<[^>]+>', ' '),
                    r'\\s+', ' '
                ))                                             AS body,
                p.permalink,
                p.created_at
            FROM `bigtribebuilders.dataform.core_posts` p
            LEFT JOIN `bigtribebuilders.dataform.core_members` m
                ON  p.creator_id = m.member_id
                AND m.client_id  = 'lesko_4022250'
            WHERE p.client_id = 'lesko_4022250'
              AND p.post_id   = CAST('{post_id}' AS INT64)
        ),

        all_comments AS (
            SELECT
                CONCAT('comment_', CAST(c.comment_id AS STRING)) AS content_id,
                'comment'                                          AS content_type,
                c.depth,
                c.reply_to_id,
                c.author_id,
                TRIM(CONCAT(
                    COALESCE(m.first_name, ''), ' ',
                    COALESCE(m.last_name,  '')
                ))                                                 AS author_name,
                CASE
                    WHEN m.network_role IN ('host', 'moderator') THEN 'team'
                    ELSE 'member'
                END                                                AS author_type,
                TRIM(REGEXP_REPLACE(
                    REGEXP_REPLACE(COALESCE(c.comment_text, ''), r'<[^>]+>', ' '),
                    r'\\s+', ' '
                ))                                                 AS body,
                c.permalink,
                c.created_at
            FROM `bigtribebuilders.dataform.core_comments` c
            LEFT JOIN `bigtribebuilders.dataform.core_members` m
                ON  c.author_id = m.member_id
                AND m.client_id = 'lesko_4022250'
            WHERE c.client_id      = 'lesko_4022250'
              AND c.targetable_id  = CAST('{post_id}' AS INT64)
              AND c.comment_status = 'active'
        )

        SELECT * FROM root_post
        UNION ALL
        SELECT * FROM all_comments
        ORDER BY created_at ASC, depth ASC
    """
    return client.query(sql).to_dataframe()


def get_member_history(member_id: int, exclude_content_id: str = None) -> pd.DataFrame:
    exclude = f"AND gt.content_id != '{exclude_content_id}'" if exclude_content_id else ""
    _gt_cols = _tickets_cols()
    _team_replied_sql = "OR gt.team_comment_replied" if "team_comment_replied" in _gt_cols else ""
    sql = f"""
        SELECT
            gt.content_id,
            gt.content_type,
            gt.thread_id,
            gt.permalink,
            LEFT(gt.body, 300) AS body_preview,
            gt.created_at,
            CASE
                WHEN gt.team_commented OR gt.team_reacted {_team_replied_sql} THEN 'answered'
                WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                WHEN gt.ticket_status = 'not_a_question'            THEN 'not_a_question'
                ELSE 'open'
            END AS ticket_status
        FROM `{config.TICKETS_TABLE}` gt
        LEFT JOIN (
            SELECT * FROM `{config.META_TABLE}`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY updated_at DESC) = 1
        ) tm ON gt.content_id = tm.content_id
        WHERE gt.member_id = {member_id}
          {exclude}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY gt.content_id ORDER BY gt.created_at DESC) = 1
        ORDER BY gt.created_at DESC
        LIMIT 20
    """
    return client.query(sql).to_dataframe()


def get_report_data(report_type: str, date_from: str, date_to: str) -> pd.DataFrame:
    if report_type == "volume":
        sql = f"""
            SELECT
                DATE(created_at)                             AS date,
                COUNT(*)                                     AS tickets_in,
                COUNTIF(ticket_status = 'closed')            AS tickets_closed
            FROM `{config.TICKETS_TABLE}`
            WHERE DATE(created_at) BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY date
            ORDER BY date
        """
    elif report_type == "response_time":
        sql = f"""
            SELECT
                TIMESTAMP_DIFF(first_engagement_at, created_at, MINUTE) AS minutes_to_response
            FROM `{config.TICKETS_TABLE}`
            WHERE first_engagement_at IS NOT NULL
              AND DATE(created_at) BETWEEN '{date_from}' AND '{date_to}'
        """
    elif report_type == "team_productivity":
        sql = f"""
            SELECT
                assigned_to,
                COUNT(*) AS tickets_closed
            FROM `{config.TICKETS_TABLE}`
            WHERE ticket_status = 'closed'
              AND DATE(ticket_updated_at) BETWEEN '{date_from}' AND '{date_to}'
              AND assigned_to IS NOT NULL AND assigned_to != ''
            GROUP BY assigned_to
            ORDER BY tickets_closed DESC
        """
    elif report_type == "domain_breakdown":
        sql = f"""
            SELECT
                COALESCE(domain, 'unset') AS domain,
                COUNT(*)                  AS tickets
            FROM `{config.TICKETS_TABLE}`
            WHERE DATE(created_at) BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY domain
            ORDER BY tickets DESC
        """
    else:
        return pd.DataFrame()

    return client.query(sql).to_dataframe()


# ── Team Feedback ─────────────────────────────────────────────────────────────

TEAM_FEEDBACK_TABLE = f"{config.PROJECT_ID}.{config.DATASET}.team_feedback"


def submit_team_feedback(submitted_by: str, feedback_type: str, title: str, body: str):
    now = datetime.datetime.utcnow().isoformat()
    fid = str(uuid.uuid4())
    safe_title = title.replace("'", "\\'")
    safe_body  = body.replace("'", "\\'")
    sql = f"""
        INSERT INTO `{TEAM_FEEDBACK_TABLE}`
          (feedback_id, submitted_by, feedback_type, title, body, status, created_at)
        VALUES
          ('{fid}', '{submitted_by}', '{feedback_type}',
           '{safe_title}',
           '{safe_body}',
           'open', TIMESTAMP '{now}')
    """
    client.query(sql).result()


def get_team_feedback() -> pd.DataFrame:
    sql = f"""
        SELECT *
        FROM `{TEAM_FEEDBACK_TABLE}`
        ORDER BY created_at DESC
    """
    return client.query(sql).to_dataframe()


def reply_team_feedback(feedback_id: str, reply_text: str, replied_by: str, new_status: str):
    now = datetime.datetime.utcnow().isoformat()
    safe_reply = reply_text.replace("'", "\\'")
    sql = f"""
        UPDATE `{TEAM_FEEDBACK_TABLE}`
        SET
          reply_text = '{safe_reply}',
          replied_by = '{replied_by}',
          replied_at = TIMESTAMP '{now}',
          status     = '{new_status}'
        WHERE feedback_id = '{feedback_id}'
    """
    client.query(sql).result()


def get_app_logs(limit: int = 100, level: str = None) -> pd.DataFrame:
    """Return recent rows from app_logs, optionally filtered by level (ERROR, WARNING, INFO)."""
    level_filter = f"AND level = '{level}'" if level else ""
    sql = f"""
        SELECT created_at, level, source, message, detail
        FROM `{config.LOGS_TABLE}`
        WHERE 1=1 {level_filter}
        ORDER BY created_at DESC
        LIMIT {int(limit)}
    """
    return client.query(sql).to_dataframe()
