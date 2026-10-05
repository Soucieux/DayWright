import { clockOfTimestamp, localDateOf } from "../time.js";

/** File kinds by extension, for imported documents. */
const FILE_KINDS = [[/\.(md|markdown)$/i, "markdown"], [/\.pdf$/i, "pdf"], [/\.docx$/i, "word"]];

/** The revision an import appends to a file's name, so a changed file is kept as a new one. */
const REVISION_SUFFIX = / · [0-9a-f]{12}$/;

/**
 * Describe a Library note or file for listing: its name and its kind.
 * @param {{title: string, sourceType: string}} source - A note or file as the local service lists it.
 * @returns {{name: string, kind: string, group: string}} `kind` is `markdown`, `pdf`, `word`, `file`
 *   or `note`; `group` is `files` for imported files and `notes` for written notes.
 */
export function sourceView(source) {
  if (source.sourceType === "document") {
    const name = source.title.replace(REVISION_SUFFIX, "");
    const kind = FILE_KINDS.find(([pattern]) => pattern.test(name))?.[1] || "file";
    return { name, kind, group: "files" };
  }
  return { name: source.title, kind: "note", group: "notes" };
}

/**
 * Say when a note or file was added: the time for today, otherwise the day and month.
 * @param {string} createdAt - When it was added, as an ISO timestamp.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @param {string} todayWord - The word for today in that language.
 * @returns {string} Such as "today 14:02", "2 Sep" or "9月2日".
 */
export function addedLabel(createdAt, today, language, todayWord) {
  if (localDateOf(createdAt) === today) return `${todayWord} ${clockOfTimestamp(createdAt)}`;
  const locale = language === "zh" ? "zh-Hans" : "en-GB";
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(new Date(createdAt));
}

/**
 * Keep the notes and files of one goal, or of one area, or all of them, in their order.
 * @param {{domain: string, goalId: string|null}[]} items - Notes and files, or search results, as the local service lists them.
 * @param {{goalId?: string, domain?: string}} scope - A goal's id, or an area, or `all`.
 * @returns {object[]} The items in that scope.
 */
export function libraryOf(items, { goalId, domain }) {
  if (goalId) return items.filter((item) => item.goalId === goalId);
  return domain && domain !== "all" ? items.filter((item) => item.domain === domain) : items;
}

/**
 * The area and goal a note or file added from a goal starts with.
 * @param {{id: string, domain: string}} goal - The goal.
 * @returns {{domain: string, goalId: string}} Its area and the goal itself.
 */
export function goalLinks(goal) {
  return { domain: goal.domain, goalId: goal.id };
}

/**
 * The area and goal a note or file added from an area's page starts with.
 * @param {string} domain - The area.
 * @returns {{domain: string, goalId: null}} The area, and no goal.
 */
export function areaLinks(domain) {
  return { domain, goalId: null };
}

/**
 * The headers that send a file to the local service: its name, which may hold any character, and its area and goal.
 * @param {string} filename - The file's name.
 * @param {{domain: string, goalId: string|null}} links - The area and goal it joins.
 * @returns {Record<string, string>} The request headers; the goal's only when there is one.
 */
export function importHeaders(filename, { domain, goalId }) {
  const headers = {
    "Content-Type": "application/octet-stream",
    "X-DayWright-Filename": btoa(String.fromCharCode(...new TextEncoder().encode(filename))),
    "X-DayWright-Area": domain,
  };
  if (goalId) headers["X-DayWright-Goal"] = goalId;
  return headers;
}

/**
 * Describe a passage that matched a search: the note or file it is from, that one's area and goal, and which part it is.
 * @param {object} match - A match as the local service returns it.
 * @returns {{name: string, domain: string, goalTitle: string|null, passage: string, part: number}} `part` counts from 1.
 */
export function matchView(match) {
  return {
    name: sourceView({ title: match.sourceTitle, sourceType: match.sourceType }).name,
    domain: match.domain,
    goalTitle: match.goalTitle,
    passage: match.content,
    part: match.chunkIndex + 1,
  };
}
