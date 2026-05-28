"""
Unit tests for mn_format — the [label](url) → clickable <a> pipeline that posts
to Mighty Networks. Pure functions, no BigQuery/network, safe to run anywhere.

These cover the markdown forms produced by static/paste_links.js when a coach
pastes rich text containing hyperlinks into the answer box.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mn_format import _linkify, build_mn_body, mn_mention


def test_markdown_link_becomes_anchor():
    out = _linkify("Apply [here](https://grants.gov/apply) for funds")
    assert out == (
        'Apply <a target="_blank" rel="noopener noreferrer nofollow" '
        'href="https://grants.gov/apply">here</a> for funds'
    )


def test_mailto_markdown_link_supported():
    out = _linkify("[email us](mailto:help@lesko.org)")
    assert 'href="mailto:help@lesko.org"' in out
    assert ">email us</a>" in out


def test_bare_url_is_linkified():
    out = _linkify("see https://sba.gov/funding now")
    assert '<a target="_blank" rel="noopener noreferrer nofollow" href="https://sba.gov/funding">https://sba.gov/funding</a>' in out


def test_surrounding_html_is_escaped():
    out = _linkify("a < b & c > d")
    assert out == "a &lt; b &amp; c &gt; d"


def test_link_label_is_escaped():
    out = _linkify("[A & B](https://x.org)")
    assert ">A &amp; B</a>" in out


def test_multiple_links():
    out = _linkify("[A](https://a.com) and [B](https://b.com)")
    assert out.count("<a ") == 2
    assert 'href="https://a.com"' in out and 'href="https://b.com"' in out


def test_plain_text_unchanged():
    assert _linkify("just a plain answer") == "just a plain answer"


def test_build_mn_body_wraps_in_paragraph():
    body = build_mn_body("hi [there](https://x.org)", False, None, "")
    assert body.startswith('<p dir="auto">') and body.endswith("</p>")
    assert 'href="https://x.org"' in body


def test_build_mn_body_prepends_mention():
    body = build_mn_body("hello", True, 12345, "Jane Doe")
    assert body.startswith(mn_mention(12345, "Jane Doe"))
    assert 'data-user-id="12345"' in body
    assert body.endswith('<p dir="auto">hello</p>')


def test_build_mn_body_no_mention_when_no_member_id():
    body = build_mn_body("hello", True, None, "Nobody")
    assert "mighty-mention" not in body
