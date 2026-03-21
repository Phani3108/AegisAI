/**
 * @fileoverview DOM assembly for attribution strip (imports tokens only).
 */

import {
  authorDisplay,
  copyrightSymbolYear,
  hrefLinkedIn,
  hrefPortfolio,
  uiSubtitle,
} from "./tokens.mjs";

export function mountAttributionFooter(rootId) {
  const root = document.getElementById(rootId);
  if (!root) return;

  root.replaceChildren();
  root.classList.add("site-footer");

  const inner = document.createElement("div");
  inner.className = "site-footer-inner";

  const line = document.createElement("p");
  line.className = "site-footer-line";
  line.append(
    document.createTextNode(`${copyrightSymbolYear()} ${authorDisplay()} · ${uiSubtitle()}`),
  );

  const nav = document.createElement("nav");
  nav.className = "site-footer-nav";
  nav.setAttribute("aria-label", "Author links");

  const mk = (label, href) => {
    const a = document.createElement("a");
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = label;
    return a;
  };

  nav.append(mk("LinkedIn", hrefLinkedIn()), mk("Site", hrefPortfolio()));

  inner.append(line, nav);
  root.append(inner);
}
