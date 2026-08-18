"""
Unit tests for mn_format — the [label](url) → clickable <a> pipeline that posts
to Mighty Networks. Pure functions, no BigQuery/network, safe to run anywhere.

These cover the markdown forms produced by static/paste_links.js when a coach
pastes rich text containing hyperlinks into the answer box.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from mn_format import _linkify, build_mn_body, mn_mention, space_label, MEMBER_BIO_LABEL


def test_space_label_member_bio_exception():
    # A comment on the member's own profile carries space_id = network id.
    assert space_label(config.MN_NETWORK_ID, {}) == MEMBER_BIO_LABEL
    assert space_label(int(config.MN_NETWORK_ID), {7159013: "x"}) == MEMBER_BIO_LABEL


def test_space_label_known_id():
    assert space_label(7159013, {7159013: "Group Coaching Classes"}) == "Group Coaching Classes"
    # string id resolves the same as int
    assert space_label("7159013", {7159013: "Group Coaching Classes"}) == "Group Coaching Classes"


def test_space_label_unknown_and_empty():
    assert space_label(999, {7159013: "x"}) == "Space 999"
    assert space_label(999, None) == "Space 999"
    assert space_label(None, {}) == "—"
    assert space_label("", {}) == "—"


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


def test_blank_line_becomes_paragraph_break():
    body = build_mn_body("First point.\n\nSecond point.", False, None, "")
    assert body == '<p dir="auto">First point.</p><p dir="auto">Second point.</p>'


def test_single_newline_becomes_br():
    body = build_mn_body("line one\nline two", False, None, "")
    assert body == '<p dir="auto">line one<br>line two</p>'


def test_multiple_blank_lines_collapse_to_one_break():
    body = build_mn_body("a\n\n\n\nb", False, None, "")
    assert body == '<p dir="auto">a</p><p dir="auto">b</p>'


def test_windows_newlines_normalized():
    body = build_mn_body("a\r\n\r\nb\r\nc", False, None, "")
    assert body == '<p dir="auto">a</p><p dir="auto">b<br>c</p>'


def test_links_still_work_across_paragraphs():
    body = build_mn_body(
        "Apply [here](https://grants.gov)\n\nOr see https://sba.gov", False, None, ""
    )
    assert body.count('<p dir="auto">') == 2
    assert 'href="https://grants.gov"' in body
    assert 'href="https://sba.gov"' in body


def test_mention_precedes_paragraphs():
    body = build_mn_body("hi\n\nbye", True, 99, "Jo")
    assert body.startswith(mn_mention(99, "Jo"))
    assert body.endswith('<p dir="auto">hi</p><p dir="auto">bye</p>')


def test_markdown_bold_becomes_strong():
    assert _linkify("make it **bold** now") == "make it <strong>bold</strong> now"


def test_markdown_italic_becomes_em():
    assert _linkify("a *little* emphasis") == "a <em>little</em> emphasis"


def test_bold_and_italic_together():
    assert _linkify("**big** and *small*") == "<strong>big</strong> and <em>small</em>"


def test_bullet_lines_not_italicized():
    # single leading "*" with no closing marker on the line stays literal
    assert _linkify("* first item") == "* first item"


def test_arithmetic_asterisks_left_alone():
    # spaces hug the * so it is not treated as italic
    assert _linkify("buy 2 * 3 widgets") == "buy 2 * 3 widgets"


def test_bold_is_escaped_safely():
    # the bold content is HTML-escaped before the <strong> wrapper is added
    assert _linkify("**a < b**") == "<strong>a &lt; b</strong>"


def test_formatting_works_through_build_mn_body():
    body = build_mn_body("**bold** and *italic* and 😀", False, None, "")
    assert body == '<p dir="auto"><strong>bold</strong> and <em>italic</em> and 😀</p>'


def test_link_and_bold_coexist():
    out = _linkify("see **this** [link](https://x.org)")
    assert "<strong>this</strong>" in out and 'href="https://x.org"' in out
