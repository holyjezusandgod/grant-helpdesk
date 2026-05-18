#!/usr/bin/env python3
"""
Cloud Run Job: send_followups
Runs daily. Finds due follow-up questions from followup_queue, checks whether
the member re-engaged since the answer was given, and either inserts a row into
bigtribebuilders.dataform.generated_comments (picked up by the existing
mightynetworks-api-post-comments service every 2 min) or marks the follow-up
as skipped.
"""

import os
import uuid
from datetime import datetime, timezone

from google.cloud import bigquery

PROJECT        = os.environ.get("GOOGLE_CLOUD_PROJECT", "bigtribebuilders")
DATASET        = "grant_helpdesk"
QUEUE_TABLE    = f"{PROJECT}.{DATASET}.followup_queue"
KEYS_TABLE     = f"{PROJECT}.{DATASET}.team_api_keys"
COMMENTS_TABLE = f"{PROJECT}.dataform.generated_comments"
MN_NETWORK_ID  = int(os.environ.get("MN_NETWORK_ID", "4022250"))


def get_api_key(bq: bigquery.Client, email: str) -> str | None:
    rows = list(bq.query(
        f"SELECT mn_api_key FROM `{KEYS_TABLE}` "
        f"WHERE email = '{email}' ORDER BY updated_at DESC LIMIT 1"
    ).result())
    return rows[0]["mn_api_key"] if rows else None


def get_admin_key(bq: bigquery.Client) -> str:
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


def update_status(bq: bigquery.Client, followup_id: str, status: str,
                  ts_col: str, reason: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    reason_sql = f"'{reason}'" if reason else "NULL"
    skipped_sql = f"TIMESTAMP '{now}'" if ts_col == "skipped_at" else "NULL"
    sent_sql    = f"TIMESTAMP '{now}'" if ts_col == "sent_at" else "NULL"
    bq.query(f"""
        UPDATE `{QUEUE_TABLE}`
        SET status = '{status}',
            sent_at = {sent_sql},
            skipped_at = {skipped_sql},
            skipped_reason = {reason_sql}
        WHERE id = '{followup_id}'
    """).result()


def main():
    bq = bigquery.Client(project=PROJECT)
    print("Fetching due follow-ups...")
    items = get_due_followups(bq)
    print(f"Found {len(items)} due.")

    sent = skipped = errors = 0

    for item in items:
        fid      = item["id"]
        cid      = item["content_id"]   # MN post_id (numeric string)
        msg      = item["message"]
        by_email = item.get("scheduled_by") or ""

        # Re-engagement check: any member activity after the follow-up was queued
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

        # Insert into generated_comments for the existing commenter service to pick up
        try:
            row = [{
                "prompt_id":          abs(hash(fid)) % (10 ** 9),  # stable int id
                "client_id":          "grant_helpdesk",
                "network_id":         MN_NETWORK_ID,
                "targetable_post_id": int(cid),
                "result":             msg,
                "api_key":            api_key,
                "next_available_ts":  datetime.now(timezone.utc).isoformat(),
                "post_status":        "now",
                "created_at":         datetime.now(timezone.utc).isoformat(),
            }]
            errors_bq = bq.insert_rows_json(COMMENTS_TABLE, row)
            if errors_bq:
                raise RuntimeError(f"BQ insert errors: {errors_bq}")

            update_status(bq, fid, "sent", "sent_at")
            print(f"  [{fid[:8]}] QUEUED to generated_comments for post {cid}")
            sent += 1
        except Exception as e:
            print(f"  [{fid[:8]}] ERROR: {e}")
            errors += 1

    print(f"\nDone — queued: {sent}, skipped: {skipped}, errors: {errors}")


if __name__ == "__main__":
    main()
