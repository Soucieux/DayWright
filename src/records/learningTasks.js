import { libraryName } from "../library/libraryData.js";
import { clockOfTimestamp } from "../time.js";

/**
 * What From a source sends to make Learning tasks: the files and pages ticked, in the order they are
 * listed; their day, or the first of them, one a day from it; the goal they join, if any; and whether
 * each starts a new pass through its file.
 * @param {{key: string, sourceId: string}[]} entries - What was listed to tick, in order.
 * @param {Set<string>} ticked - The keys ticked.
 * @param {object} choices - The sheet's choices.
 * @param {string} choices.date - The day, YYYY-MM-DD.
 * @param {string} choices.spread - `allOn` or `oneADay`; one file has nothing to spread.
 * @param {string} choices.goal - "" for none, `new` for a new goal, or an existing goal's id.
 * @param {string} choices.newGoal - A new goal's name.
 * @param {boolean} choices.fresh - Start fresh rather than carry on each file's latest pass.
 * @returns {{sourceIds: string[], date: string, oneADay: boolean, goal: object|null, fresh: boolean}} The request.
 */
export function fromSourceRequest(entries, ticked, { date, spread, goal, newGoal, fresh }) {
  const sourceIds = entries.filter((entry) => ticked.has(entry.key)).map((entry) => entry.sourceId);
  return { sourceIds, date, oneADay: spread === "oneADay" && sourceIds.length > 1,
    goal: goal === "new" ? { title: newGoal.trim() } : goal ? { goalId: goal } : null, fresh: Boolean(fresh) };
}

/**
 * What a checklist item is marked with: the user's own, or, for one from the source, how the source's
 * latest reading found it, in a website's words or a file's.
 * @param {{addedBy: string, pageState: string}} entry - The item.
 * @param {string|null} origin - Where the task's source came from: `website`, `folder`, `file`, or none.
 * @returns {string|null} The mark's message key, or null for none.
 */
export function checklistMark(entry, origin) {
  if (entry.addedBy === "you") return "checklistYours";
  if (!entry.pageState) return null;
  const page = origin === "website";
  if (entry.pageState === "new") return page ? "checklistNewOnPage" : "checklistNewInFile";
  return page ? "checklistGoneFromPage" : "checklistGoneFromFile";
}

/**
 * Where Alt+↑ or Alt+↓ moves an item: one place up or down the list, never past either end.
 * @param {{id: string}[]} checklist - The items on show, in order.
 * @param {string} id - The item moved.
 * @param {number} step - -1 up, 1 down.
 * @returns {number|null} Its new place, or null when it is at that end already.
 */
export function movedIndex(checklist, id, step) {
  const next = checklist.findIndex((entry) => entry.id === id) + step;
  return next >= 0 && next < checklist.length ? next : null;
}

/**
 * Whether the task's sheet suggests marking it Done: every item ticked, the task not done yet, and the
 * suggestion not set aside with Not now. Ticking never marks it Done itself.
 * @param {string} status - The task's status.
 * @param {{allTicked: boolean}|null} learned - Its checklist.
 * @param {boolean} dismissed - Whether Not now set it aside.
 * @returns {boolean} Whether to show the suggestion.
 */
export function suggestsDone(status, learned, dismissed) {
  return Boolean(learned?.allTicked) && status !== "done" && !dismissed;
}

/**
 * Whether the task's sheet offers Continue next session: the task partly done, with items left to study,
 * unticked and still in their source.
 * @param {string} status - The task's status.
 * @param {{checklist: object[]}|null} learned - Its checklist.
 * @returns {boolean} Whether to offer it.
 */
export function offersContinue(status, learned) {
  return status === "partial" && Boolean(learned?.checklist.some((entry) => !entry.tickedAt && entry.pageState !== "gone"));
}

/**
 * What Continue next session sends Ava, in the words she reads.
 * @param {string} title - The task's title.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} The request.
 */
export function continueRequest(title, t) {
  return t("avaContinueRequest", { title });
}

/**
 * What a past day's checklist puts in Ava's box, to send or change: ticking its first item not ticked, or,
 * with every item ticked, unticking its last.
 * @param {string} title - The task's title.
 * @param {{title: string, tickedAt: string|null}[]} checklist - Its items on show.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} The request.
 */
export function pastTickRequest(title, checklist, t) {
  const open = checklist.find((entry) => !entry.tickedAt);
  return open ? t("avaTickRequest", { item: open.title, title })
    : t("avaUntickRequest", { item: checklist[checklist.length - 1].title, title });
}

/**
 * What the briefing says of a website's look-up as its task started: that it brought the task up to date,
 * and when, or that the site couldn't be reached; nothing when it was unchanged or not checked yet.
 * @param {{startCheck: string, startCheckedAt: string|null}} learned - The task's check.
 * @returns {{key: string, time?: string}|null} The line's message key and time, or null.
 */
export function startCheckLine({ startCheck, startCheckedAt }) {
  if (startCheck === "updated") return { key: "websiteUpdatedAt", time: clockOfTimestamp(startCheckedAt) };
  return startCheck === "unreachable" ? { key: "websiteCheckFailed" } : null;
}

/**
 * Every Library item a Learn task uses, by the name the Library shows: the one its checklist came from first,
 * then those it links.
 * @param {{sourceId: string|null, sourceTitle: string|null, references: {title: string}[]}} learned - The task's
 *   checklist and links, as the local service gives them.
 * @returns {string[]} Their names.
 */
export function linkedNames({ sourceId, sourceTitle, references }) {
  return [...(sourceId && sourceTitle ? [libraryName(sourceTitle)] : []), ...references.map((reference) => reference.title)];
}

/**
 * Names as one list in words: "A", "A and B", "A, B and C", or in Chinese "A、B和C".
 * @param {string[]} names - The names, in order.
 * @param {string} language - `en` or `zh`.
 * @returns {string} The list.
 */
export function namesList(names, language) {
  if (names.length < 2) return names.join("");
  const [last, rest] = [names[names.length - 1], names.slice(0, -1)];
  return language === "zh" ? `${rest.join("、")}和${last}` : `${rest.join(", ")} and ${last}`;
}
