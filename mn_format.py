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

# Markdown bold/italic. The marker must hug the text (no space just inside), so
# bullet lines ("* item") and arithmetic ("2 * 3") are left alone. Bold runs
# first so its ** is consumed before the single-* italic pass. MN renders the
# resulting <strong>/<em> tags (its own editor emits the same).
_MD_BOLD_RE   = re.compile(r'\*\*(\S(?:.*?\S)?)\*\*')
_MD_ITALIC_RE = re.compile(r'\*(\S(?:.*?\S)?)\*')

_LINK_TAG = '<a target="_blank" rel="noopener noreferrer nofollow" href="{url}">{label}</a>'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(s: str) -> str:
    """HTML-escape plain text, then apply markdown bold/italic.

    Escaping happens first so the <strong>/<em> tags we add are the only live
    HTML — anything the coach typed (stray <, >) stays inert text.
    """
    safe = _esc(s)
    safe = _MD_BOLD_RE.sub(r'<strong>\1</strong>', safe)
    safe = _MD_ITALIC_RE.sub(r'<em>\1</em>', safe)
    return safe


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
                out.append(_fmt(part))
        if i + 2 < len(chunks):
            label = _fmt(chunks[i + 1])
            url = chunks[i + 2]
            out.append(_LINK_TAG.format(url=url, label=label))
    return "".join(out)


def _paragraphize(text: str) -> str:
    """Convert plain-text line structure into the HTML MN renders.

    Blank lines separate <p dir="auto"> paragraphs; single newlines inside a
    paragraph become <br>. Without this, newlines reach MN as literal \\n
    inside one <p> and HTML collapses them — answers show up "consolidated".
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paras = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paras:
        return '<p dir="auto"></p>'
    return "".join(
        '<p dir="auto">' + "<br>".join(_linkify(line) for line in p.split("\n")) + "</p>"
        for p in paras
    )


def build_mn_body(text: str, tag_member: bool, member_id, member_name: str,
                  extra_mentions=None) -> str:
    """Wrap plain text in HTML and prepend @mentions.

    extra_mentions: optional iterable of (member_id, name) tuples for tagging
    colleagues in addition to (or instead of) the member.
    """
    prefix = ""
    if tag_member and member_id:
        prefix += mn_mention(member_id, member_name)
    for _mid, _name in (extra_mentions or []):
        prefix += mn_mention(_mid, _name)
    return prefix + _paragraphize(text)
