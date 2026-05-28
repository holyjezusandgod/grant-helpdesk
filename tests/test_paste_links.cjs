// Unit tests for static/paste_links.js htmlToMarkdown().
//
// Run:  npm i jsdom  (once, anywhere)  then
//       NODE_PATH=<dir>/node_modules node tests/test_paste_links.cjs
//
// Exercises the exact browser conversion code under jsdom's DOMParser.

const { JSDOM } = require("jsdom");
const dom = new JSDOM("<!doctype html><html><body></body></html>");
global.DOMParser = dom.window.DOMParser;

const { htmlToMarkdown, cleanUrl } = require("../static/paste_links.js");

let pass = 0, fail = 0;
function eq(name, got, want) {
  if (got === want) {
    pass++;
    console.log("ok   - " + name);
  } else {
    fail++;
    console.log("FAIL - " + name);
    console.log("        got:  " + JSON.stringify(got));
    console.log("        want: " + JSON.stringify(want));
  }
}

// 1. embedded link inside a sentence
eq(
  "embedded link",
  htmlToMarkdown('<p>Apply <a href="https://grants.gov/apply">here</a> for funds</p>'),
  "Apply [here](https://grants.gov/apply) for funds"
);

// 2. Google Docs redirect wrapper is unwrapped
eq(
  "google redirect unwrap",
  htmlToMarkdown('<a href="https://www.google.com/url?q=https://grants.gov/apply&sa=D&source=docs">apply</a>'),
  "[apply](https://grants.gov/apply)"
);

// 3. plain text, no links, untouched
eq("plain text", htmlToMarkdown("<p>just text</p>"), "just text");

// 4. mailto links are kept (server _linkify also accepts mailto)
eq(
  "mailto link",
  htmlToMarkdown('<a href="mailto:help@lesko.org">email us</a>'),
  "[email us](mailto:help@lesko.org)"
);

// 5. dangerous schemes dropped, visible text preserved
eq(
  "javascript scheme dropped",
  htmlToMarkdown('<a href="javascript:void(0)">click</a>'),
  "click"
);

// 6. multiple links across block elements → newlines between
eq(
  "multiple links + blocks",
  htmlToMarkdown('<div>See <a href="https://a.com">A</a></div><div>and <a href="https://b.com">B</a></div>'),
  "See [A](https://a.com)\nand [B](https://b.com)"
);

// 7. brackets in the label are stripped to keep markdown well-formed
eq(
  "brackets in label stripped",
  htmlToMarkdown('<a href="https://x.com">[VA] form</a>'),
  "[VA form](https://x.com)"
);

// 8. cleanUrl direct
eq("cleanUrl passthrough", cleanUrl("https://grants.gov/x"), "https://grants.gov/x");
eq(
  "cleanUrl google unwrap",
  cleanUrl("https://www.google.com/url?q=https://x.org/a%3Fb%3D1&sa=D"),
  "https://x.org/a?b=1"
);

// 9. real-ish Google Docs paste: nested spans + redirect link
eq(
  "google docs nested spans",
  htmlToMarkdown(
    '<b style="font-weight:normal"><span style="font-size:11pt">Check the </span>' +
    '<span><a href="https://www.google.com/url?q=https://sba.gov/funding&sa=D">' +
    '<span style="color:#1155cc;text-decoration:underline">SBA funding page</span></a></span>' +
    '<span> today.</span></b>'
  ),
  "Check the [SBA funding page](https://sba.gov/funding) today."
);

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
