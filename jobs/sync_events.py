#!/usr/bin/env python3
"""
Cloud Run Job: sync_events
Fetches upcoming RSVP-enabled events from Mighty Networks and writes them
to grant_helpdesk.upcoming_events in BigQuery.
Runs daily via Cloud Scheduler.
"""

import os
import json
import urllib.request
from datetime import datetime, timezone

from google.cloud import bigquery

PROJECT    = os.environ.get("GOOGLE_CLOUD_PROJECT", "bigtribebuilders")
DATASET    = "grant_helpdesk"
TABLE      = f"{PROJECT}.{DATASET}.upcoming_events"
KEYS_TABLE = f"{PROJECT}.{DATASET}.team_api_keys"
NETWORK_ID = os.environ.get("MN_NETWORK_ID", "4022250")
MN_API_BASE = "https://api.mn.co/admin/v1"


def get_admin_key(bq: bigquery.Client) -> str:
    rows = list(bq.query(
        f"SELECT mn_api_key FROM `{KEYS_TABLE}` WHERE mn_api_key IS NOT NULL LIMIT 1"
    ).result())
    if not rows:
        raise RuntimeError("No MN API key found in team_api_keys")
    return rows[0]["mn_api_key"]


def fetch_upcoming_events(api_key: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    events = []
    page = 1
    while True:
        url = f"{MN_API_BASE}/networks/{NETWORK_ID}/events?per_page=50&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "events-sync-job/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        items = data.get("items", [])
        if not items:
            break

        has_future = False
        for e in items:
            starts_at_str = e.get("starts_at", "")
            if not starts_at_str:
                continue
            starts_at = datetime.fromisoformat(starts_at_str)
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=timezone.utc)
            if starts_at > now:
                has_future = True
                if e.get("rsvp_enabled") and not e.get("rsvp_closed"):
                    events.append(e)

        # Events are newest-first; once a full page has no future events, stop
        if not has_future:
            break

        if not data.get("links", {}).get("next"):
            break
        page += 1

    return events


def write_to_bq(bq: bigquery.Client, events: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()

    # Truncate and replace
    bq.query(f"DELETE FROM `{TABLE}` WHERE TRUE").result()

    if not events:
        print("No upcoming events found — table cleared.")
        return

    rows = []
    for e in events:
        rows.append({
            "event_id":     e["id"],
            "title":        e.get("title", ""),
            "starts_at":    e.get("starts_at"),
            "ends_at":      e.get("ends_at"),
            "time_zone":    e.get("time_zone", ""),
            "event_type":   e.get("event_type", ""),
            "zoom_link":    e.get("link", ""),
            "permalink":    e.get("permalink", ""),
            "rsvp_enabled": e.get("rsvp_enabled", True),
            "rsvp_closed":  e.get("rsvp_closed", False),
            "refreshed_at": now,
        })

    errors = bq.insert_rows_json(TABLE, rows)
    if errors:
        raise RuntimeError(f"BQ insert errors: {errors}")

    print(f"Wrote {len(rows)} upcoming events to {TABLE}")


def main():
    bq = bigquery.Client(project=PROJECT)
    print("Fetching admin API key...")
    api_key = get_admin_key(bq)
    print("Fetching upcoming events from Mighty Networks...")
    events = fetch_upcoming_events(api_key)
    print(f"Found {len(events)} upcoming RSVP-enabled events")
    write_to_bq(bq, events)
    print("Done.")


if __name__ == "__main__":
    main()
