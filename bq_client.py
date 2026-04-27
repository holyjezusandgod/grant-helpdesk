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


def get_unreviewed_rejects() -> pd.DataFrame:
    """Posts/articles/comments the classifier rejected and the team hasn't reviewed yet."""
    sql = f"""
        SELECT *
        FROM `{config.TICKETS_TABLE}`
        WHERE ticket_status = 'not_a_question'
          AND manual_status IS NULL
        ORDER BY created_at DESC
    """
    return client.query(sql).to_dataframe()


def get_team_members() -> list[str]:
    sql = f"""
        SELECT full_name
        FROM `{config.TEAM_TABLE}`
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
    filters = []

    if status and status != "All":
        filters.append(f"ticket_status = '{status}'")
    else:
        # Feedback statuses are hidden from the default view
        filters.append(f"ticket_status NOT IN ('not_a_question', 'confirmed_question')")
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

    # Build EXCEPT and CASE clauses based on what columns actually exist in the table.
    # This makes the query forward/backward compatible as Dataform rebuilds the schema.
    _gt_cols = {f.name for f in client.get_table(config.TICKETS_TABLE).schema}
    _team_replied_sql = "OR gt.team_comment_replied" if "team_comment_replied" in _gt_cols else ""
    _always_except = ["assigned_to", "manual_status", "domain", "ticket_status"]
    _optional_except = ["difficulty", "team_comment_replied"]
    _except_cols = ", ".join(_always_except + [c for c in _optional_except if c in _gt_cols])

    sql = f"""
        WITH live AS (
            SELECT
                gt.* EXCEPT({_except_cols}),
                COALESCE(tm.assigned_to, gt.assigned_to)               AS assigned_to,
                tm.status                                               AS manual_status,
                COALESCE(tm.domain, gt.domain)                          AS domain,
                CASE
                    WHEN gt.team_commented OR gt.team_reacted {_team_replied_sql} THEN 'answered'
                    WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                    WHEN gt.ticket_status = 'not_a_question'            THEN 'not_a_question'
                    ELSE 'open'
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
            LEFT(body, 120) AS body_preview,
            CASE
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24 THEN 'normal'
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 48 THEN 'urgent'
                ELSE 'critical'
            END AS urgency
        FROM live
        {where}
        ORDER BY created_at DESC
    """
    df = client.query(sql).to_dataframe()
    if "domain" not in df.columns:
        df["domain"] = None
    return df


def get_ticket_detail(content_id: str) -> dict:
    _gt_cols = {f.name for f in client.get_table(config.TICKETS_TABLE).schema}
    _team_replied_sql = "OR gt.team_comment_replied" if "team_comment_replied" in _gt_cols else ""
    _always_except = ["assigned_to", "manual_status", "domain", "ticket_status"]
    _optional_except = ["difficulty", "team_comment_replied"]
    _except_cols = ", ".join(_always_except + [c for c in _optional_except if c in _gt_cols])
    sql = f"""
        SELECT
            gt.* EXCEPT({_except_cols}),
            COALESCE(tm.assigned_to, gt.assigned_to)               AS assigned_to,
            tm.status                                               AS manual_status,
            COALESCE(tm.domain, gt.domain)                          AS domain,
            CASE
                WHEN gt.team_commented OR gt.team_reacted {_team_replied_sql} THEN 'answered'
                WHEN tm.status IS NOT NULL AND tm.status != ''      THEN tm.status
                WHEN gt.ticket_status = 'not_a_question'            THEN 'not_a_question'
                ELSE 'open'
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
    df = client.query(sql).to_dataframe()
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


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


def post_mn_comment(post_id: str, body: str, api_key: str, reply_to_id: int = None) -> dict:
    """Post a comment to Mighty Networks via the API. Returns the created comment dict."""
    import urllib.request, json as _json
    url = f"{config.MN_API_BASE}/networks/{config.MN_NETWORK_ID}/posts/{post_id}/comments"
    payload = {"text": body}
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    data = _json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return _json.loads(resp.read())


def update_ticket_meta(
    content_id: str,
    status: str,
    assigned_to: str,
    domain: str = None,
    feedback_reason: str = None,
):
    now        = datetime.datetime.utcnow().isoformat()
    domain_val = domain or ""
    reason_val = (feedback_reason or "").replace("'", "\\'")
    sql = f"""
        MERGE `{config.META_TABLE}` T
        USING (
            SELECT
                '{content_id}'     AS content_id,
                '{status}'         AS status,
                '{assigned_to}'    AS assigned_to,
                '{domain_val}'     AS domain,
                '{reason_val}'     AS feedback_reason,
                TIMESTAMP '{now}'  AS updated_at
        ) S
        ON T.content_id = S.content_id
        WHEN MATCHED THEN UPDATE SET
            status          = S.status,
            assigned_to     = S.assigned_to,
            domain          = S.domain,
            feedback_reason = S.feedback_reason,
            updated_at      = S.updated_at
        WHEN NOT MATCHED THEN INSERT
            (content_id, status, assigned_to, domain, feedback_reason, updated_at)
        VALUES
            (S.content_id, S.status, S.assigned_to, S.domain, S.feedback_reason, S.updated_at)
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
                        project=config.PROJECT_ID,
                        dataset=config.DATASET,
                        name="grant_member_assignments",
                    ),
                    dataform_v1beta1.Target(
                        project=config.PROJECT_ID,
                        dataset=config.DATASET,
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


def get_open_stats() -> dict:
    # 'open' is the default status in the view; 'new'/'assigned' are manual overrides.
    # All three mean the ticket is still unresolved.
    sql = f"""
        SELECT
            COUNTIF(ticket_status IN ('open', 'new', 'assigned'))                                       AS open,
            COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24)                         AS normal,
            COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) BETWEEN 24 AND 47)            AS urgent,
            COUNTIF(ticket_status IN ('open', 'new', 'assigned')
                AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) >= 48)                        AS critical
        FROM `{config.TICKETS_TABLE}`
    """
    row = client.query(sql).to_dataframe().iloc[0]
    return row.to_dict()


def get_daily_stats() -> dict:
    # 'answered' = team engaged; 'closed' = manually closed — both count as resolved.
    sql = f"""
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
        FROM `{config.TICKETS_TABLE}`
    """
    row = client.query(sql).to_dataframe().iloc[0]
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
    exclude = f"AND content_id != '{exclude_content_id}'" if exclude_content_id else ""
    sql = f"""
        SELECT
            content_id,
            content_type,
            LEFT(body, 120) AS body_preview,
            created_at,
            ticket_status
        FROM `{config.TICKETS_TABLE}`
        WHERE member_id = {member_id}
        {exclude}
        ORDER BY created_at DESC
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
