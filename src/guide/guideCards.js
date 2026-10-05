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
 * How many words a card's For, Do and Rule lines hold together, its title and their labels left out.
 * @param {{for: string, do: string, rule: string}} card - The card.
 * @returns {number} The words: runs between spaces holding a letter or a digit, so “+ is none and 09:00–22:00 is one.
 */
export function cardWords(card) {
  return [card.for, card.do, card.rule].join(" ").split(/\s+/).filter((word) => /[\p{L}\p{N}]/u.test(word)).length;
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
