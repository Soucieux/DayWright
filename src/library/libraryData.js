import { clockOfTimestamp, localDateOf } from "../time.js";

/** File kinds by extension, for imported documents. */
const FILE_KINDS = [[/\.(md|markdown)$/i, "markdown"], [/\.pdf$/i, "pdf"], [/\.docx$/i, "word"]];

/** The revision an import appends to a file's name, so a changed file is kept as a new one. */
const REVISION_SUFFIX = / · [0-9a-f]{12}$/;

/** A briefing shorter than this says too little, so Ava may suggest one, as the local service's briefings decide. */
const BRIEFING_MIN_WORDS = 4;

/**
 * Describe a Library item for listing: its name and its kind.
 * @param {{title: string, sourceType?: string, origin?: string, relativePath?: string}} source - An item as the local service lists it.
 * @returns {{name: string, kind: string, group: string}} `kind` is `markdown`, `pdf`, `word`, `file`, `website`
 *   or `note`; `group` is `folders` for a connected folder's files, `websites`, `files` for imported files
 *   and `notes` for written notes.
 */
export function sourceView(source) {
  if (source.origin === "folder") {
    const kind = FILE_KINDS.find(([pattern]) => pattern.test(source.relativePath || ""))?.[1] || "file";
    return { name: source.title, kind, group: "folders" };
  }
  if (source.origin === "website") return { name: source.title, kind: "website", group: "websites" };
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

/**
 * The Library's items by where each came from: each connected folder with its files in path order,
 * then websites, imported files and notes, newest first. A folder shows in its own area, and in any
 * area one of its files was moved to.
 * @param {object[]} items - Every item, newest first, as the local service lists them.
 * @param {object[]} folders - The connected folders.
 * @param {string} domain - An area, or `all`.
 * @returns {{folders: {folder: object, items: object[]}[], website: object[], file: object[], note: object[]}} The groups.
 */
export function libraryGroups(items, folders, domain) {
  const shown = libraryOf(items, { domain });
  const byPath = (one, other) => (one.relativePath || "").localeCompare(other.relativePath || "");
  const of = (origin) => shown.filter((item) => (item.origin || (item.sourceType === "note" ? "note" : "file")) === origin);
  return {
    folders: folders
      .map((folder) => ({ folder, items: shown.filter((item) => item.folderId === folder.id).sort(byPath) }))
      .filter(({ folder, items: inFolder }) => domain === "all" || folder.domain === domain || inFolder.length),
    website: of("website"),
    file: of("file"),
    note: of("note"),
  };
}

/**
 * The items whose name, briefing or headings hold the words looked for, in their order.
 * @param {object[]} items - Library items.
 * @param {string} query - What the user typed.
 * @returns {object[]} The items that match; none for nothing typed.
 */
export function findInLibrary(items, query) {
  const wanted = query.trim().toLowerCase();
  if (!wanted) return [];
  const words = (item) => [sourceView(item).name, item.briefing || "",
    ...(item.outline || []).flatMap((group) => [group.title, ...group.topics.map((topic) => topic.title)])].join("\n").toLowerCase();
  return items.filter((item) => words(item).includes(wanted));
}

/**
 * How an item opens: a connected folder's file in its app while the folder and the file are found, and
 * on its folder's website when it has one; a website in the browser. A note or an imported file keeps
 * only its text, so it opens nowhere.
 * @param {object} source - The item.
 * @param {object|undefined} folder - Its connected folder, for a folder's file.
 * @returns {{app: boolean, website: boolean, browser: boolean}} Each way it opens.
 */
export function openActions(source, folder) {
  if (source.origin === "website") return { app: false, website: false, browser: true };
  if (source.origin !== "folder" || !folder) return { app: false, website: false, browser: false };
  return { app: Boolean(folder.found && !source.missing), website: Boolean(folder.website), browser: false };
}

/**
 * Whether an item lacks a briefing or headings of its own, so Ava may suggest them. A website keeps only
 * its own headings, so only its briefing can be missing.
 * @param {{briefing?: string|null, outline?: object[], origin?: string}} source - The item.
 * @returns {boolean} True when Ava may suggest a briefing or headings.
 */
export function wantsBriefing(source) {
  const words = (source.briefing || "").split(/\s+/).filter(Boolean).length;
  return words < BRIEFING_MIN_WORDS || (!(source.outline || []).length && source.origin !== "website");
}

/**
 * What an item's briefing shows: what it is about, who said so, and its first-level headings each with
 * its second-level ones. Its text is never shown.
 * @param {object} source - The item.
 * @returns {{text: string|null, by: string, headings: {title: string, topics: string[]}[], outlineBy: string, wants: boolean}}
 *   `by` and `outlineBy` are `source`, `ava`, `you` or "" for none.
 */
export function briefingView(source) {
  return {
    text: source.briefing || null,
    by: source.briefingBy || "",
    headings: (source.outline || []).map((group) => ({ title: group.title, topics: group.topics.map((topic) => topic.title) })),
    outlineBy: source.outlineBy || "",
    wants: wantsBriefing(source),
  };
}

/**
 * The files Locate offers for a file not found in its folder: the folder's readable files, ticked or
 * not, but none too large to read, nor its own old place. A file Refresh added as new, as it does one
 * renamed and changed, is offered too, so the file located takes it over; one linked to a goal is
 * not, as the local service keeps it.
 * @param {{files: {path: string, reason: string|null}[]}} preview - The folder's tree, as read now.
 * @param {{relativePath: string, goalId: string|null}[]} inFolder - The folder's items in the Library.
 * @param {{relativePath: string}} missing - The file not found.
 * @returns {string[]} Their paths in the folder.
 */
export function locateChoices(preview, inFolder, missing) {
  const linked = new Set(inFolder.filter((item) => item.goalId).map((item) => item.relativePath));
  return preview.files.filter((file) => file.reason !== "too large" && file.path !== missing.relativePath && !linked.has(file.path))
    .map((file) => file.path);
}
