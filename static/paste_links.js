// Smart paste for the Lesko Help Desk answer fields.
//
// A plain <textarea> only receives the text/plain flavour of the clipboard, so
// any hyperlink embedded in rich text (Google Docs, Gmail, a web page) is lost
// before Python ever sees it. This script listens for paste events on the
// textareas in the parent Streamlit document, reads the text/html flavour, and
// rewrites <a href> links as [label](url) markdown — which the server-side
// _linkify() already turns into clickable <a> tags when posting to MN.
//
// Single source of truth: app.py embeds this file in a components.html iframe,
// and tests/test_paste_links.mjs exercises htmlToMarkdown() under jsdom.

(function () {
  "use strict";

  function cleanUrl(href) {
    if (!href) return "";
    href = String(href).trim();
    // Google Docs rewrites links as https://www.google.com/url?q=REAL&sa=...
    try {
      var u = new URL(href);
      if (/(^|\.)google\.[a-z.]+$/i.test(u.hostname) && u.pathname === "/url") {
        var q = u.searchParams.get("q");
        if (q) return q;
      }
    } catch (e) {
      // relative or malformed URL — leave as-is
    }
    return href;
  }

  function isAllowedHref(href) {
    return /^(https?:\/\/|mailto:)/i.test(href || "");
  }

  // Flatten pasted HTML to text, turning <a href> into [label](url).
  // Block-level elements become line breaks; all other formatting is dropped.
  function htmlToMarkdown(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var out = [];

    function pushText(t) {
      if (t) out.push(t.replace(/\s+/g, " "));
    }

    var BLOCK = {
      P: 1, DIV: 1, LI: 1, TR: 1, UL: 1, OL: 1, BLOCKQUOTE: 1, TABLE: 1,
      SECTION: 1, ARTICLE: 1, HEADER: 1, FOOTER: 1,
      H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1,
    };

    function walk(node) {
      var kids = node.childNodes;
      for (var i = 0; i < kids.length; i++) {
        var c = kids[i];
        if (c.nodeType === 3) {
          pushText(c.nodeValue);
        } else if (c.nodeType === 1) {
          var tag = c.tagName;
          if (tag === "STYLE" || tag === "SCRIPT" || tag === "HEAD") continue;
          if (tag === "A") {
            var href = cleanUrl(c.getAttribute("href") || "");
            var label = (c.textContent || "").replace(/\s+/g, " ").trim();
            if (isAllowedHref(href) && label) {
              out.push("[" + label.replace(/[\[\]]/g, "") + "](" + href + ")");
            } else {
              pushText(c.textContent);
            }
            continue;
          }
          if (tag === "BR") { out.push("\n"); continue; }
          walk(c);
          if (BLOCK[tag]) out.push("\n"); // newline after a block, not before
        }
      }
    }

    walk(doc.body || doc);

    var text = out.join("");
    text = text.replace(/[ \t]+/g, " ");
    text = text.replace(/ *\n */g, "\n");
    text = text.replace(/\n{3,}/g, "\n\n");
    return text.trim();
  }

  // ── node test hook ───────────────────────────────────────────────────────
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { htmlToMarkdown: htmlToMarkdown, cleanUrl: cleanUrl };
  }

  // ── browser installer ────────────────────────────────────────────────────
  if (typeof window === "undefined" || !window.parent) return;
  var pdoc;
  try {
    pdoc = window.parent.document;
  } catch (e) {
    return; // cross-origin iframe — cannot reach the textareas
  }
  if (!pdoc || window.parent.__leskoPasteLinksInstalled) return;
  window.parent.__leskoPasteLinksInstalled = true;

  function setValue(el, value) {
    var proto = window.parent.HTMLTextAreaElement && window.parent.HTMLTextAreaElement.prototype;
    var desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
  }

  pdoc.addEventListener(
    "paste",
    function (e) {
      var el = e.target;
      if (!el || el.tagName !== "TEXTAREA") return;
      var cd = e.clipboardData || window.parent.clipboardData;
      if (!cd) return;
      var html = cd.getData("text/html");
      if (!html || !/<a[\s>]/i.test(html)) return; // no links → normal paste
      var md = htmlToMarkdown(html);
      if (!md) return;
      e.preventDefault();
      var start = el.selectionStart, end = el.selectionEnd;
      var v = el.value;
      setValue(el, v.slice(0, start) + md + v.slice(end));
      var caret = start + md.length;
      el.selectionStart = el.selectionEnd = caret;
      el.dispatchEvent(new window.parent.Event("input", { bubbles: true }));
    },
    true
  );
})();
