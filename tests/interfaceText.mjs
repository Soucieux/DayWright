import { readFileSync } from "node:fs";

/**
 * What the interface tests share: the interface's text in both languages and a message looked up in it, a stand-in
 * lookup that shows which message was asked for, a file under src as text, a Guide card, and a rule in the stylesheet.
 */

/** The messages, read once, the first time a lookup needs them. */
let messages;

/** The Guide's cards, read once, the first time a card is looked up. */
let guideCards;

/**
 * A file under src, as text, for the tests that check how the interface is written.
 * @param {string} path - Its path from src, such as "ui/TabList.jsx" or "../backend/app/wording.py".
 * @returns {string} Its text.
 */
export function source(path) {
  return readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
}

/**
 * The Guide's card with this id, as guide.json holds it.
 * @param {string} id - The card's id, such as "today".
 * @returns {object|undefined} The card, or undefined when no card has that id.
 */
export function guideCard(id) {
  guideCards ??= JSON.parse(source("guide/guide.json")).sections.flatMap((section) => section.cards);
  return guideCards.find((card) => card.id === id);
}

/**
 * The interface's text in both languages, read from i18n.jsx, which node can't import as it holds JSX.
 * @returns {{en: Record<string, string>, zh: Record<string, string>}} Each language's messages by key.
 */
export function interfaceText() {
  const text = source("i18n.jsx");
  const opening = "const messages = ";
  const start = text.indexOf(opening) + opening.length;
  return new Function(`return ${text.slice(start, text.indexOf("\n};\n", start) + 2)}`)();
}

/**
 * The interface's own lookup in one language: a message with its values put in, any it isn't given left as written.
 * @param {"en"|"zh"} language - The language.
 * @returns {(key: string, values?: object) => string} The lookup, which throws for a key the language lacks.
 */
export function say(language) {
  return (key, values = {}) => {
    messages ??= interfaceText();
    const message = messages[language][key];
    if (message === undefined) throw new Error(`${language} has no message ${key}`);
    return message.replace(/\{(\w+)\}/g, (match, name) => String(values[name] ?? match));
  };
}

/**
 * A stand-in for the interface's lookup that shows which message was asked for and with what, as "key" or
 * 'key {"count":2}'.
 * @param {string} key - The message asked for.
 * @param {object} [values] - Its values.
 * @returns {string} The key, and the values as JSON when there are any.
 */
export function keyText(key, values) {
  return values ? `${key} ${JSON.stringify(values)}` : key;
}

/**
 * The declarations of the stylesheet's rule written with exactly this selector at a line's start.
 * @param {string} selector - Its selector, such as ".dw-pane" or '.dw-pane[aria-selected="true"]'.
 * @returns {string} Its declarations, or "" when src/bench.css has no such rule.
 */
export function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return source("bench.css").match(new RegExp(`(?:^|\\n)${escaped} \\{([^}]*)\\}`))?.[1] ?? "";
}
