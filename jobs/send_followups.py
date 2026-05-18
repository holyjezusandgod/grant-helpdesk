#!/usr/bin/env python3
"""
Cloud Run Job: send_followups
Runs daily. Finds due follow-up questions from followup_queue, checks whether
the member re-engaged since the answer was given, and either posts the follow-up
as a comment on the original thread or marks it skipped.
"""

import os
import json
import urllib.request
from datetime import datetime, timezone

from google.cloud import bigquery

PROJECT    = os.environ.get("GOOGLE_CLOUD_PROJECT", "bigtribebuilders")
DATASET    = "grant_helpdesk"
QUEUE_TABLE = f"{PROJECT}.{DATASET}.followup_queue"
KEYS_TABLE  = f"{PROJECT}.{DATASET}.team_api_keys"
MN_API_BASE = "https://api.mn.co/admin/v1"
MN_NETWORK_ID = os.environ.get("MN_NETWORK_ID", "4022250")


def get_api_key(bq: bigquery.Client, email: str) -> str | None:
    rows = list(bq.query(
        f"SELECT mn_api_key FROM `{KEYS_TABLE}` WHERE email = '{email}' ORDER BY updated_at DESC LIMIT 1"
    ).result())
    return rows[0]["mn_api_key"] if rows else None


def get_admin_key(bq: bigquery.Client) -> str:
    """Fallback: return any available API key from the team."""
    rows = list(bq.query(
        f"SELECT mn_api_key FROM `{KEYS_TABLE}` WHERE mn_api_key IS NOT NULL LIMIT 1"
    ).result())
    if not rows:
        raise RuntimeError("No MN API key found in team_api_keys")
    return rows[0]["mn_api_key"]


def get_due_followups(bq: bigquery.Client) -> list[dict]:
    sql = f"""
        SELECT
            fq.id,
            fq.content_id,
            fq.content_type,
            fq.member_id,
            fq.member_name,
            fq.message,
            fq.scheduled_by,
            fq.created_at,
            gt.last_member_activity_at
        FROM `{QUEUE_TABLE}` fq
        LEFT JOIN (
            SELECT content_id, last_member_activity_at
            FROM `{PROJECT}.{DATASET}.grant_tickets`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY created_at DESC) = 1
        ) gt ON fq.ticket_id = gt.content_id
        WHERE fq.status = 'pending'
          AND fq.send_after <= CURRENT_TIMESTAMP()
    """
    return [dict(row) for row in bq.query(sql).result()]


def post_comment(post_id: str, body: str, api_key: str) -> None:
    url = f"{MN_API_BASE}/networks/{MN_NETWORK_ID}/posts/{int(post_id)}/comments"
    payload = json.dumps({"text": body}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
            "User-Agent":    "followup-job/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"MN API returned {resp.status}")


def update_status(bq: bigquery.Client, followup_id: str, status: str,
                  ts_col: str, reason: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    reason_sql = f"'{reason}'" if reason else "NULL"
    skipped_sql = f"TIMESTAMP '{now}'" if ts_col == "skipped_at" else "NULL"
    sent_sql    = f"TIMESTAMP '{now}'" if ts_col == "sent_at" else "NULL"
    sql = f"""
        UPDATE `{QUEUE_TABLE}`
        SET status         = '{status}',
            sent_at        = {sent_sql},
            skipped_at     = {skipped_sql},
            skipped_reason = {reason_sql}
        WHERE id = '{followup_id}'
    """
    bq.query(sql).result()


def main():
    bq = bigquery.Client(project=PROJECT)
    now = datetime.now(timezone.utc)

    print("Fetching due follow-ups...")
    items = get_due_followups(bq)
    print(f"Found {len(items)} due.")

    sent = skipped = errors = 0

    for item in items:
        fid      = item["id"]
        cid      = item["content_id"]
        msg      = item["message"]
        by_email = item.get("scheduled_by") or ""

        # Check re-engagement: any member activity after the follow-up was created
        last_activity = item.get("last_member_activity_at")
        fu_created    = item.get("created_at")
        if last_activity and fu_created:
            if hasattr(last_activity, "tzinfo") and last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            if hasattr(fu_created, "tzinfo") and fu_created.tzinfo is None:
                fu_created = fu_created.replace(tzinfo=timezone.utc)
            if last_activity > fu_created:
                print(f"  [{fid[:8]}] SKIP — member re-engaged after answer")
                update_status(bq, fid, "skipped", "skipped_at", "member_re-engaged")
                skipped += 1
                continue

        # Get API key
        api_key = (get_api_key(bq, by_email) if by_email else None) or get_admin_key(bq)

        try:
            post_comment(cid, msg, api_key)
            update_status(bq, fid, "sent", "sent_at")
            print(f"  [{fid[:8]}] SENT to post {cid}")
            sent += 1
        except Exception as e:
            print(f"  [{fid[:8]}] ERROR: {e}")
            errors += 1

    print(f"\nDone — sent: {sent}, skipped: {skipped}, errors: {errors}")


if __name__ == "__main__":
    main()
