import uuid
import datetime
import pandas as pd
from google.cloud import bigquery
import config

client = bigquery.Client(project=config.PROJECT_ID)


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
    difficulty=None,
    domain=None,
) -> pd.DataFrame:
    filters = []

    if status and status != "All":
        filters.append(f"ticket_status = '{status}'")
    if assignee and assignee != "All":
        filters.append(f"assigned_to = '{assignee}'")
    if member_id:
        filters.append(f"CAST(member_id AS STRING) = '{member_id}'")
    if difficulty and difficulty != "All":
        filters.append(f"LOWER(difficulty) = '{difficulty.lower()}'")
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

    sql = f"""
        SELECT
            *,
            LEFT(body, 120) AS body_preview,
            CASE
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24 THEN 'normal'
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 48 THEN 'urgent'
                ELSE 'critical'
            END AS urgency
        FROM `{config.TICKETS_TABLE}`
        {where}
        ORDER BY created_at DESC
    """
    df = client.query(sql).to_dataframe()
    # difficulty and domain columns are added by migration 001 + Dataform redeploy;
    # fall back to None until that's done so the app doesn't crash
    for col in ("difficulty", "domain"):
        if col not in df.columns:
            df[col] = None
    return df


def get_ticket_detail(content_id: str) -> dict:
    sql = f"""
        SELECT *,
            CASE
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24 THEN 'normal'
                WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 48 THEN 'urgent'
                ELSE 'critical'
            END AS urgency
        FROM `{config.TICKETS_TABLE}`
        WHERE content_id = '{content_id}'
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


def update_ticket_meta(
    content_id: str,
    status: str,
    assigned_to: str,
    difficulty: str = None,
    domain: str = None,
):
    now = datetime.datetime.utcnow().isoformat()
    difficulty_val = difficulty or ""
    domain_val     = domain or ""
    sql = f"""
        MERGE `{config.META_TABLE}` T
        USING (
            SELECT
                '{content_id}'     AS content_id,
                '{status}'         AS status,
                '{assigned_to}'    AS assigned_to,
                '{difficulty_val}' AS difficulty,
                '{domain_val}'     AS domain,
                TIMESTAMP '{now}'  AS updated_at
        ) S
        ON T.content_id = S.content_id
        WHEN MATCHED THEN UPDATE SET
            status      = S.status,
            assigned_to = S.assigned_to,
            difficulty  = S.difficulty,
            domain      = S.domain,
            updated_at  = S.updated_at
        WHEN NOT MATCHED THEN INSERT
            (content_id, status, assigned_to, difficulty, domain, updated_at)
        VALUES
            (S.content_id, S.status, S.assigned_to, S.difficulty, S.domain, S.updated_at)
    """
    client.query(sql).result()


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
