import { clockOfTimestamp, localDateOf } from "../time.js";

/** Where a topic lookup goes when the user allows one. The local service fetches from this host only. */
export const PUBLIC_SOURCE_HOST = "en.wikipedia.org";

/** File kinds by extension, for imported documents. */
const FILE_KINDS = [[/\.(md|markdown)$/i, "markdown"], [/\.pdf$/i, "pdf"], [/\.docx$/i, "word"]];

/** The revision an import appends to a file's name, so a changed file is kept as a new source. */
const REVISION_SUFFIX = / · [0-9a-f]{12}$/;

/**
 * Describe a Library source for listing: its name, its kind, and whether it came from the web.
 * @param {{title: string, sourceType: string, sourceUrl?: string}} source - A source as the local service lists it.
 * @returns {{name: string, kind: string, group: string, fromWeb: boolean}} `kind` is `markdown`, `pdf`,
 *   `word`, `file` or `note`; `group` is `files` for imported files and `notes` for everything else.
 */
export function sourceView(source) {
  if (source.sourceType === "document") {
    const name = source.title.replace(REVISION_SUFFIX, "");
    const kind = FILE_KINDS.find(([pattern]) => pattern.test(name))?.[1] || "file";
    return { name, kind, group: "files", fromWeb: false };
  }
  return { name: source.title, kind: "note", group: "notes", fromWeb: Boolean(source.sourceUrl) };
}

/**
 * Say when a source was added: the time for today, otherwise the day and month.
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
 * Keep the network log entries made on one local date.
 * @param {{happenedAt: string}[]} entries - Network log entries.
 * @param {string} date - A YYYY-MM-DD date.
 * @returns {object[]} The entries made on that date, in their original order.
 */
export function entriesOn(entries, date) {
  return entries.filter((entry) => localDateOf(entry.happenedAt) === date);
}
