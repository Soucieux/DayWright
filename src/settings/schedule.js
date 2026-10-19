/**
 * Settings › Schedule's words: countries and regions named in the interface's language, a holiday's name, when the
 * holidays were imported, and what keeps a work schedule from being saved. Nothing here reads the service; the pane
 * passes in what it gave.
 */

/** A name written in Chinese characters. */
const CHINESE = /[㐀-鿿]/;

/**
 * A country's name in the interface's language, from the Mac's own names for regions; its code when it has none.
 * @param {string} code - Its ISO 3166-1 code, such as `CA`.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Canada" or "加拿大".
 */
export function countryName(code, language) {
  try {
    return new Intl.DisplayNames([language === "zh" ? "zh-Hans" : "en-GB"], { type: "region" }).of(code) || code;
  } catch {
    return code;
  }
}

/**
 * The countries to choose from, by name in the interface's language.
 * @param {string[]} codes - The countries DayWright can import holidays for.
 * @param {string} language - `en` or `zh`.
 * @returns {{value: string, label: string}[]} Each country, sorted by its name.
 */
export function countryOptions(codes, language) {
  const locale = language === "zh" ? "zh-Hans" : "en-GB";
  return codes.map((code) => ({ value: code, label: countryName(code, language) }))
    .sort((first, second) => first.label.localeCompare(second.label, locale));
}

/**
 * A region's name: in the interface's language where DayWright has it, else in English, else its code.
 * @param {string} code - Its ISO 3166-2 code, such as `CA-ON`.
 * @param {Record<string, {en: string, zh?: string}>} names - The names DayWright comes with.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Ontario", "安大略省" or "CA-QC".
 */
export function regionName(code, names, language) {
  const named = names[code];
  return named?.[language] || named?.en || code;
}

/**
 * The regions to choose from: national holidays alone first, then each region the holidays imported name, by name.
 * @param {string[]} regions - The regions with holidays of their own.
 * @param {Record<string, {en: string, zh?: string}>} names - The names DayWright comes with.
 * @param {string} language - `en` or `zh`.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {{value: string, label: string}[]} The options; national holidays alone have the value "".
 */
export function regionOptions(regions, names, language, t) {
  const locale = language === "zh" ? "zh-Hans" : "en-GB";
  return [{ value: "", label: t("holidaysNationalOnly") }, ...regions.map((code) => ({ value: code, label: regionName(code, names, language) }))
    .sort((first, second) => first.label.localeCompare(second.label, locale))];
}

/**
 * A holiday's name: in Chinese, its local name when that is written in Chinese; otherwise its English one.
 * @param {{name: string, localName: string}} holiday - As the service gives it.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Thanksgiving" or "春节".
 */
export function holidayName(holiday, language) {
  return language === "zh" && CHINESE.test(holiday.localName || "") ? holiday.localName : holiday.name;
}

/**
 * A holiday's date as the list of holidays shows it, with its year, as the list holds two.
 * @param {string} date - YYYY-MM-DD.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Mon, 12 Oct 2026" or "2026年10月12日周一".
 */
export function holidayDate(date, language) {
  return new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${date}T12:00:00`));
}

/**
 * When the holidays kept were imported, and for which years; or that none are yet.
 * @param {{importedAt: string|null, years: number[]}} view - The holidays as Settings › Schedule shows them.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Last imported 19 October 2026, for 2026 and 2027."
 */
export function importedLine(view, t, language) {
  if (!view.importedAt) return t("holidaysNotImported");
  const date = new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${view.importedAt.slice(0, 10)}T12:00:00`));
  const years = view.years.join(language === "zh" ? " 和 " : " and ");
  return t("holidaysImportedOn", { date, years });
}

/**
 * What keeps a work schedule from being saved: an end that isn't after its start, or no day ticked.
 * @param {{start: string, end: string, days: number[]}} schedule - The schedule as the pane holds it.
 * @returns {string|null} The key of the words saying so, or null when it can be saved.
 */
export function scheduleProblem(schedule) {
  if (!schedule.start || !schedule.end || schedule.end <= schedule.start) return "workScheduleEndAfterStart";
  if (!schedule.days.length) return "workScheduleNeedsDay";
  return null;
}
