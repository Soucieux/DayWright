import { clockOfTimestamp, localDateOf } from "../time.js";
import { BRIEFING_MIN_WORDS, countWords, cutWords } from "../wording.js";

/** File kinds by extension, for imported documents. */
const FILE_KINDS = [[/\.(md|markdown)$/i, "markdown"], [/\.pdf$/i, "pdf"], [/\.docx$/i, "word"]];

/** The revision an import appends to a file's name, so a changed file is kept as a new one. */
const REVISION_SUFFIX = / · [0-9a-f]{12}$/;

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
 * A Library item's name as the Library shows it: an imported file's without the revision its import added.
 * @param {string} title - Its title as the local service keeps it.
 * @returns {string} Its name.
 */
export function libraryName(title) {
  return title.replace(REVISION_SUFFIX, "");
}

/**
 * The Library items a goal holds: those one of its tasks uses. Items link no goal of their own.
 * @param {{tasks?: {goalId: string|null}[]}[]} items - Every item, with the tasks that use it.
 * @param {string} goalId - The goal.
 * @returns {object[]} Its items, in the Library's order.
 */
export function goalSources(items, goalId) {
  return items.filter((item) => (item.tasks || []).some((task) => task.goalId === goalId));
}

/**
 * The tasks that use a Library item, under their goals, as its briefing lists them: each goal's tasks together,
 * in the order the local service gives them (goals by title, tasks without a goal last).
 * @param {{goalId: string|null, goalTitle: string|null}[]} tasks - The tasks that use the item.
 * @returns {{goalId: string|null, goalTitle: string|null, tasks: object[]}[]} One group per goal, and one for none.
 */
export function tasksByGoal(tasks) {
  const groups = [];
  for (const task of tasks) {
    const last = groups[groups.length - 1];
    if (last && last.goalId === task.goalId) last.tasks.push(task);
    else groups.push({ goalId: task.goalId, goalTitle: task.goalTitle, tasks: [task] });
  }
  return groups;
}

/**
 * The Library items a Learn task can link: each one it doesn't use yet, by name.
 * @param {{id: string, title: string}[]} items - Every item.
 * @param {string[]} linkedIds - The items the task uses already, as its checklist's own or a reference.
 * @returns {object[]} The items it may link.
 */
export function linkChoices(items, linkedIds) {
  return items.filter((item) => !linkedIds.includes(item.id))
    .sort((one, other) => libraryName(one.title).localeCompare(libraryName(other.title)));
}

/**
 * The items Learn's Library card lists: those a task uses first, then the rest, each part in the Library's
 * order, newest first.
 * @param {{tasks?: object[]}[]} items - Every item, newest first, with the tasks that use it.
 * @returns {object[]} The items in the card's order.
 */
export function studyLibrary(items) {
  const used = (item) => Boolean(item.tasks?.length);
  return [...items.filter(used), ...items.filter((item) => !used(item))];
}

/**
 * The headers that send a file to the local service: its name, which may hold any character.
 * @param {string} filename - The file's name.
 * @returns {Record<string, string>} The request headers.
 */
export function importHeaders(filename) {
  return {
    "Content-Type": "application/octet-stream",
    "X-DayWright-Filename": btoa(String.fromCharCode(...new TextEncoder().encode(filename))),
  };
}

/**
 * Describe a passage that matched a search: the item it is from, and which part it is.
 * @param {object} match - A match as the local service returns it.
 * @returns {{name: string, passage: string, part: number}} `part` counts from 1.
 */
export function matchView(match) {
  return {
    name: sourceView({ title: match.sourceTitle, sourceType: match.sourceType }).name,
    passage: match.content,
    part: match.chunkIndex + 1,
  };
}

/**
 * The Library's items by where each came from: each connected folder with its files in path order,
 * then websites, imported files and notes, newest first.
 * @param {object[]} items - Every item, newest first, as the local service lists them.
 * @param {object[]} folders - The connected folders.
 * @returns {{folders: {folder: object, items: object[]}[], website: object[], file: object[], note: object[]}} The groups.
 */
export function libraryGroups(items, folders) {
  const byPath = (one, other) => (one.relativePath || "").localeCompare(other.relativePath || "");
  const of = (origin) => items.filter((item) => (item.origin || (item.sourceType === "note" ? "note" : "file")) === origin);
  return {
    folders: folders.map((folder) => ({ folder, items: items.filter((item) => item.folderId === folder.id).sort(byPath) })),
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
 * on its folder's website when it has one; a website in the browser; a file imported from the Mac's own
 * window in its app, where it is, while it is there. A note, or a file imported from the browser or
 * before DayWright remembered where from, keeps only its text, so it opens nowhere.
 * @param {object} source - The item.
 * @param {object|undefined} folder - Its connected folder, for a folder's file.
 * @returns {{app: boolean, website: boolean, browser: boolean}} Each way it opens.
 */
export function openActions(source, folder) {
  if (source.origin === "website") return { app: false, website: false, browser: true };
  if (source.originalPath) return { app: Boolean(source.originalFound), website: false, browser: false };
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
  return countWords(source.briefing) < BRIEFING_MIN_WORDS || (!(source.outline || []).length && source.origin !== "website");
}

/**
 * What an item's briefing shows: what it is about, to the word limit, who said so, and its first-level headings
 * each with its second-level ones. Its text is never shown.
 * @param {object} source - The item.
 * @returns {{text: string|null, by: string, headings: {title: string, topics: string[]}[], outlineBy: string, wants: boolean}}
 *   `by` and `outlineBy` are `source`, `ava`, `you` or "" for none.
 */
export function briefingView(source) {
  return {
    // Held to the word limit, a briefing kept before it was included.
    text: cutWords(source.briefing) || null,
    by: source.briefingBy || "",
    headings: (source.outline || []).map((group) => ({ title: group.title, topics: group.topics.map((topic) => topic.title) })),
    outlineBy: source.outlineBy || "",
    wants: wantsBriefing(source),
  };
}

/**
 * The files Locate offers for a file not found in its folder: the folder's readable files, ticked or
 * not, but none too large to read, nor its own old place. A file Refresh added as new, as it does one
 * renamed and changed, is offered too, so the file located takes it over; one a task uses is not, as
 * the local service keeps it.
 * @param {{files: {path: string, reason: string|null}[]}} preview - The folder's tree, as read now.
 * @param {{relativePath: string, tasks?: object[]}[]} inFolder - The folder's items in the Library, each with
 *   the tasks that use it.
 * @param {{relativePath: string}} missing - The file not found.
 * @returns {string[]} Their paths in the folder.
 */
export function locateChoices(preview, inFolder, missing) {
  const used = new Set(inFolder.filter((item) => item.tasks?.length).map((item) => item.relativePath));
  return preview.files.filter((file) => file.reason !== "too large" && file.path !== missing.relativePath && !used.has(file.path))
    .map((file) => file.path);
}
