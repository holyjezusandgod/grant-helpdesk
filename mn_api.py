"""
Mighty Networks Admin API calls.

Standalone HTTP module — no BigQuery dependencies. All calls hit the MN REST API
and raise RuntimeError on non-2xx responses.
"""

import requests as _requests

import config


def mn_promote_to_host(member_id: int, admin_api_key: str) -> dict:
    """Promote a community member to host role via MN Admin API."""
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


def rsvp_member_to_event(event_id: int, member_id: str, api_key: str) -> None:
    """RSVP a member to a Mighty Networks event via the Admin API."""
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


def delete_mn_post(post_id: str, api_key: str) -> None:
    """Delete a post from Mighty Networks via the Admin API."""
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
