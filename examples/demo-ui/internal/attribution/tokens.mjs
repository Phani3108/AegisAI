/**
 * @fileoverview Fragmented attribution tokens (Lab UI). Not a license grant.
 * Removing this file breaks the footer mount in bootstrap.mjs.
 */

const chr = (...codes) => String.fromCharCode(...codes);

export function copyrightSymbolYear() {
  return [chr(169), chr(32), chr(50), chr(48), chr(50), chr(54)].join("");
}

export function authorDisplay() {
  const a = [chr(80), chr(104), chr(97), chr(110), chr(105)].join("");
  const b = [chr(77), chr(97), chr(114), chr(117), chr(112), chr(97), chr(107), chr(97)].join("");
  return `${a} ${b}`;
}

export function uiSubtitle() {
  return [chr(65), chr(101), chr(103), chr(105), chr(115), chr(65), chr(73), chr(32), chr(76), chr(97), chr(98)].join("");
}

export function hrefLinkedIn() {
  const chunks = [
    "ht",
    "tps:",
    "//",
    "www.lin",
    "kedin.com/",
    "in/",
    "phani-marupaka",
  ];
  return chunks.join("");
}

export function hrefPortfolio() {
  const chunks = ["ht", "tps:", "//", "phani", "marupaka.", "netlify", ".app"];
  return chunks.join("");
}
