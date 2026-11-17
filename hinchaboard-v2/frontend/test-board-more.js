// Optional jsdom smoke test for the "show more" control.
// Run: node frontend/test-board-more.js (requires jsdom: npm i jsdom)
let jsdom;
try { jsdom = require("jsdom"); } catch { console.log("skip: jsdom not installed"); process.exit(0); }
const fs = require("fs");
const { JSDOM, VirtualConsole } = jsdom;
const assert = require("assert");
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => errors.push(e.message));
const dom = new JSDOM(fs.readFileSync(require("path").join(__dirname, "..", "preview.html"), "utf8"), {
  url: "http://localhost/", runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
});
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  await wait(250);
  const d = dom.window.document;
  const more = d.getElementById("boardMore");
  const rows = () => d.querySelectorAll("#board .row").length;
  assert.equal(rows(), 20);
  assert.equal(more.getAttribute("aria-expanded"), "false");
  more.click();
  assert.equal(more.getAttribute("aria-expanded"), "true");
  assert.equal(rows(), 44);
  assert.equal(more.textContent, "Show less");
  more.click();
  assert.equal(rows(), 20);
  assert.match(more.textContent, /Show more \(\d+\)/);
  assert.deepEqual(errors, []);
  console.log("frontend board-more smoke test passed");
  dom.window.close();
})().catch((e) => { console.error(e); process.exit(1); });
