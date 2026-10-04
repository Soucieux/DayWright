import { agentName } from "../ui/agentName.js";

/** The start of the key of a sentence saying why a plan was suggested; the rest say what sets it apart. */
const WHY_PREFIX = "planWhy";
/** The key of a reason the local model wrote, in English (`en`) and Chinese (`zh`), when it chose the plan. */
const AGENT_REASON = "planWhyAgent";
/** The values of a sentence that hold one task's title; a list of titles is always a title list. */
const TITLE_VALUES = new Set(["title", "first", "usual", "often"]);
/** The value of a sentence that lists the agents who voted for a plan, by their keys. */
const AGENTS_VALUE = "agents";

/**
 * Word one of a plan's sentences. English is the planner's own wording; another language words it
 * from its key, translating and quoting task titles, and falls back to English for a sentence it
 * has no wording for.
 * @param {{key: string, values: object, text: string}} note - The sentence as the planner stores it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @param {(value: string) => string} demoText - Translates the demo workspace's own words.
 * @returns {string} The sentence.
 */
function noteText(note, t, language, demoText) {
  if (language === "en") return note.text;
  const values = Object.fromEntries(Object.entries(note.values).map(([name, value]) => [
    name,
    name === AGENTS_VALUE ? value.map((key) => agentName(key, t)).join(t("listSeparator"))
      : Array.isArray(value) ? value.map((title) => `“${demoText(title)}”`).join(t("listSeparator"))
        : TITLE_VALUES.has(name) ? demoText(value) : value,
  ]));
  const worded = t(note.key, values);
  return worded === note.key ? note.text : worded;
}

/**
 * Say why a plan was suggested and what sets it apart from the others, in the interface language.
 * A plan proposed before plans kept their sentences says it all in one text.
 * @param {{rationale?: string, notes?: object[]}} variant - The plan.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @param {(value: string) => string} demoText - Translates the demo workspace's own words.
 * @returns {{why: string, apart: string, byAgent: boolean}} Why it was suggested (empty for
 *   Balanced), what sets it apart, and whether the local model gave the reason.
 */
export function planNotes(variant, t, language, demoText) {
  const notes = variant.notes || [];
  if (!notes.length) return { why: "", apart: demoText(variant.rationale || ""), byAgent: false };
  const join = (list) => list.map((note) => noteText(note, t, language, demoText)).join(language === "en" ? " " : "");
  return {
    why: join(notes.filter((note) => note.key.startsWith(WHY_PREFIX))),
    apart: join(notes.filter((note) => !note.key.startsWith(WHY_PREFIX))),
    byAgent: notes.some((note) => note.key === AGENT_REASON),
  };
}
