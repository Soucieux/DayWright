import { countWords } from "../wording.js";

/**
 * The Guide's sections in order, each with its cards, or with only the cards a screen's "?" opens; a
 * section left with none is left out.
 * @param {object} guide - The Guide, as src/guide/guide.json holds it.
 * @param {string} [screen] - The screen whose cards to keep, as the Guide's `screens` names it; all of them without one.
 * @returns {{id: string, title: string, cards: object[]}[]} The sections.
 */
export function guideSections(guide, screen) {
  if (!screen) return guide.sections;
  const shown = guide.screens[screen];
  return guide.sections.map((section) => ({ ...section, cards: section.cards.filter((card) => shown.includes(card.id)) }))
    .filter((section) => section.cards.length > 0);
}

/**
 * The Guide's section a screen's "?" leads to: the first its cards fall in.
 * @param {object} guide - The Guide.
 * @param {string} screen - The screen, as the Guide's `screens` names it.
 * @returns {string|undefined} The section's id.
 */
export function screenSection(guide, screen) {
  return guideSections(guide, screen)[0]?.id;
}

/** The Guide's screen of each place with a "?", by the place's tab: every area but Learn shows Areas' cards. */
const SCREEN_OF_TAB = {
  today: "today", plans: "plans", calendar: "calendar", goals: "goals", tasks: "tasks", library: "library",
  learning: "learning", life: "areas", work: "areas", project: "areas",
};

/**
 * The Guide's screen whose cards a place's "?" opens, so the top bar's Guide can start at its section.
 * @param {string} tab - The place on show.
 * @returns {string|null} The screen, or null for a place with no "?".
 */
export function guideScreenOf(tab) {
  return SCREEN_OF_TAB[tab] || null;
}

/** The room between a "?" and its popover, which its pointer fills, and the least it keeps from the window's edges. */
const POPOVER_GAP = 8;
const POPOVER_EDGE = 8;
/** How far the pointer keeps from the popover's own sides, clear of its round corners. */
const POINTER_INSET = 16;

/**
 * Where a "?"'s popover goes: centred under its "?", shifted to stay inside the window, above it when there's no room
 * below, and below, kept inside the window, when there's room on neither side; with its pointer under the "?".
 * @param {{left: number, top: number, right: number, bottom: number}} anchor - The "?"'s box.
 * @param {{width: number, height: number}} size - The popover's size.
 * @param {{width: number, height: number}} view - The window's size.
 * @returns {{left: number, top: number, placement: "below"|"above", pointer: number}} Its place, which side of the "?"
 *   it is on, and its pointer's distance from its left side.
 */
export function popoverPlace(anchor, size, view) {
  const centre = (anchor.left + anchor.right) / 2;
  const left = Math.max(POPOVER_EDGE, Math.min(centre - size.width / 2, view.width - POPOVER_EDGE - size.width));
  const below = anchor.bottom + POPOVER_GAP;
  const above = anchor.top - POPOVER_GAP - size.height;
  const roomBelow = below + size.height <= view.height - POPOVER_EDGE;
  const placement = roomBelow || above < POPOVER_EDGE ? "below" : "above";
  const top = placement === "above" ? above : Math.max(POPOVER_EDGE, Math.min(below, view.height - POPOVER_EDGE - size.height));
  const pointer = Math.max(POINTER_INSET, Math.min(centre - left, size.width - POINTER_INSET));
  return { left, top, placement, pointer };
}

/**
 * How many words a card's For, Do and Rule lines hold together, its title and their labels left out.
 * @param {{for: string, do: string, rule: string}} card - The card.
 * @returns {number} The words: runs between spaces holding a letter or a digit, so “+ is none and 09:00–22:00 is one.
 */
export function cardWords(card) {
  return countWords([card.for, card.do, card.rule].join(" "));
}

/**
 * The Guide grid's rows: each section heading a row as tall as it needs, and every row of cards one
 * share of a single height, so every card is as tall as the tallest.
 * @param {{cards: unknown[]}[]} sections - The sections on show.
 * @param {number} columns - Cards to a row.
 * @returns {string} The rows, as `grid-template-rows` takes them.
 */
export function guideRows(sections, columns) {
  return sections.map((section) => ["auto", ...Array(Math.ceil(section.cards.length / columns)).fill("1fr")].join(" ")).join(" ");
}

/**
 * Split the See Guide line that ends Ava's answer from the Guide's cards off the rest of the reply.
 * @param {object} guide - The Guide.
 * @param {string} text - The reply.
 * @returns {{text: string, cards: object[]}} The text before the line and the cards it names, in its
 *   order; the whole text and no cards when the reply doesn't end with such a line, or it names a
 *   card the Guide doesn't have.
 */
export function seeGuide(guide, text) {
  const opening = `${guide.labels.seeGuide}: `;
  const start = text.lastIndexOf(opening);
  if (start < 0 || (start > 0 && text[start - 1] !== "\n") || text.includes("\n", start)) return { text, cards: [] };
  const cards = guide.sections.flatMap((section) => section.cards);
  const named = text.slice(start + opening.length).split(", ").map((title) => cards.find((card) => card.title === title));
  return named.includes(undefined) ? { text, cards: [] } : { text: text.slice(0, start).trimEnd(), cards: named };
}
