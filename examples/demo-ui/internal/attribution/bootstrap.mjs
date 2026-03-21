/**
 * @fileoverview Entry: wires attribution UI. Depends on ./render.mjs + ./tokens.mjs.
 */

import { mountAttributionFooter } from "./render.mjs";

const ROOT = "site-footer-root";

function run() {
  mountAttributionFooter(ROOT);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", run, { once: true });
} else {
  run();
}
