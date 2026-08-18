#!/usr/bin/env python3
"""
Cloud Run Job: sync_spaces
Fetches the network's spaces (channels) from Mighty Networks and writes their
id → name mapping to grant_helpdesk.space_names in BigQuery.

The helpdesk uses this to label which space a ticket was commented in. Spaces
change rarely, so this runs monthly via Cloud Scheduler (0 6 1 * *).
"""

import os
import json
import urllib.request
from datetime import datetime, timezone

from google.cloud import bigquery

PROJECT     = os.environ.get("GOOGLE_CLOUD_PROJECT", "bigtribebuilders")
DATASET     = "grant_helpdesk"
TABLE       = f"{PROJECT}.{DATASET}.space_names"
KEYS_TABLE  = f"{PROJECT}.{DATASET}.team_api_keys"
NETWORK_ID  = os.environ.get("MN_NETWORK_ID", "4022250")
MN_API_BASE = "https://api.mn.co/admin/v1"


def get_admin_key(bq: bigquery.Client) -> str:
    rows = list(bq.query(
        f"SELECT mn_api_key FROM `{KEYS_TABLE}` WHERE mn_api_key IS NOT NULL LIMIT 1"
    ).result())
    if not rows:
        raise RuntimeError("No MN API key found in team_api_keys")
    return rows[0]["mn_api_key"]


def fetch_spaces(api_key: str) -> list[dict]:
    spaces = []
    page = 1
    while True:
        url = f"{MN_API_BASE}/networks/{NETWORK_ID}/spaces?per_page=50&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "spaces-sync-job/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        items = data.get("items", [])
        if not items:
            break
        spaces.extend(items)

        if not data.get("links", {}).get("next"):
            break
        page += 1

    return spaces


def write_to_bq(bq: bigquery.Client, spaces: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for s in spaces:
        sid = s.get("id")
        name = s.get("name")
        if sid is None or not name:
            continue
        rows.append({
            "space_id":     int(sid),
            "space_name":   name,
            "refreshed_at": now,
        })

    # Atomic full-replace via a load job (WRITE_TRUNCATE). Unlike DELETE + streaming
    # insert, this never conflicts with the streaming buffer, so back-to-back runs
    # are safe. Empty result → TRUNCATE the table (DDL is streaming-buffer-safe).
    if not rows:
        bq.query(f"TRUNCATE TABLE `{TABLE}`").result()
        print("No spaces found — table truncated.")
        return

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("space_id",     "INT64"),
            bigquery.SchemaField("space_name",   "STRING"),
            bigquery.SchemaField("refreshed_at", "TIMESTAMP"),
        ],
    )
    bq.load_table_from_json(rows, TABLE, job_config=job_config).result()
    print(f"Wrote {len(rows)} spaces to {TABLE}")


def main():
    bq = bigquery.Client(project=PROJECT)
    print("Fetching admin API key...")
    api_key = get_admin_key(bq)
    print("Fetching spaces from Mighty Networks...")
    spaces = fetch_spaces(api_key)
    print(f"Found {len(spaces)} spaces")
    write_to_bq(bq, spaces)
    print("Done.")


if __name__ == "__main__":
    main()
