"""
Mighty Networks comment-body formatting — pure helpers, no Streamlit deps.

Coaches type (or paste) plain text. Links arrive as [label](url) markdown —
either typed by hand or rewritten from pasted rich text by static/paste_links.js.
_linkify() turns that markdown (and any bare URLs) into the clickable <a> tags
that MN renders, and build_mn_body() wraps the result for the Admin API.
"""

import re

_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(((?:https?://|mailto:)[^\s)]+)\)')
_URL_RE = re.compile(r'(https?://[^\s<>&"]+)')

_LINK_TAG = '<a target="_blank" rel="noopener noreferrer nofollow" href="{url}">{label}</a>'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mn_mention(member_id, member_name: str) -> str:
    """Return the HTML snippet MN uses for a @mention tag."""
    url = f"https://lesko-help-2.mn.co/members/{member_id}"
    return (
        f'<p dir="auto"><a class="mighty-mention navigate" '
        f'data-user-id="{member_id}" href="{url}">{member_name}</a></p>'
    )


def _linkify(text: str) -> str:
    """Convert [text](url) markdown links and bare URLs into clickable <a> tags."""
    chunks = _MD_LINK_RE.split(text)
    out = []
    for i in range(0, len(chunks), 3):
        plain = chunks[i]
        parts = _URL_RE.split(plain)
        for j, part in enumerate(parts):
            if j % 2 == 1:
                out.append(_LINK_TAG.format(url=part, label=part))
            else:
                out.append(_esc(part))
        if i + 2 < len(chunks):
            label = _esc(chunks[i + 1])
            url = chunks[i + 2]
            out.append(_LINK_TAG.format(url=url, label=label))
    return "".join(out)


def build_mn_body(text: str, tag_member: bool, member_id, member_name: str) -> str:
    """Wrap plain text in HTML and prepend a @mention if requested."""
    safe = _linkify(text)
    if tag_member and member_id:
        return mn_mention(member_id, member_name) + f'<p dir="auto">{safe}</p>'
    return f'<p dir="auto">{safe}</p>'
