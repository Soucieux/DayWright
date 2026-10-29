/** Minutes in a day, for wrapping times past midnight. */
export const MINUTES_PER_DAY = 24 * 60;
/** One minute, in milliseconds. */
export const MINUTE_MS = 60 * 1000;
/** One day, in milliseconds. */
export const DAY_MS = MINUTES_PER_DAY * MINUTE_MS;

/**
 * The locale dates and numbers are written in for the interface language.
 * @param {string} language - `en` or `zh`.
 * @returns {string} `zh-Hans` for Chinese, else `en-GB`.
 */
export function localeOf(language) {
  return language === "zh" ? "zh-Hans" : "en-GB";
}

/**
 * Convert an HH:MM time to minutes after midnight.
 * @param {string} time - A 24-hour HH:MM time.
 * @returns {number} Minutes after midnight.
 */
export function minutesOf(time) {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 60 + minute;
}

/**
 * Format minutes after midnight as HH:MM, wrapping past midnight.
 * @param {number} minutes - Minutes after midnight; may exceed one day.
 * @returns {string} A 24-hour HH:MM time.
 */
export function clockOf(minutes) {
  const wrapped = ((minutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  return `${String(Math.floor(wrapped / 60)).padStart(2, "0")}:${String(wrapped % 60).padStart(2, "0")}`;
}

/**
 * Describe when something starts and ends.
 * @param {string} start - Its HH:MM start time.
 * @param {number} durationMinutes - How long it lasts.
 * @returns {string} The range, such as `17:30–18:00`; one ending at midnight ends at `24:00`.
 */
export function timeRange(start, durationMinutes) {
  const end = minutesOf(start) + durationMinutes;
  return `${start}–${end === MINUTES_PER_DAY ? "24:00" : clockOf(end)}`;
}

/**
 * Format a length of time the way the interface reads it aloud: "45 min", "1 h", "3 h 30 min".
 * @param {number} minutes - A whole number of minutes.
 * @param {string} language - `en` or `zh`.
 * @returns {string} The duration in the interface language.
 */
export function formatMinutes(minutes, language) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (language === "zh") {
    if (!hours) return `${rest} 分钟`;
    return rest ? `${hours} 小时 ${rest} 分` : `${hours} 小时`;
  }
  if (!hours) return `${rest} min`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/**
 * Name a date's weekday and its day and month, for page headings.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {{weekday: string, dayMonth: string}} Such as "Wednesday" and "23 September".
 */
export function longDate(value, language) {
  const date = new Date(`${value}T12:00:00`);
  const locale = localeOf(language);
  return {
    weekday: new Intl.DateTimeFormat(locale, { weekday: "long" }).format(date),
    dayMonth: new Intl.DateTimeFormat(locale, { day: "numeric", month: "long" }).format(date),
  };
}

/**
 * Name a date in full for a heading, in the language's own order.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Wednesday 23 September" or "9月23日星期三".
 */
export function fullDate(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { weekday: "long", day: "numeric", month: "long" })
    .format(new Date(`${value}T12:00:00`));
}

/**
 * Name a moment by its local date and time to the minute, as a goal's span reads it.
 * @param {string} value - An ISO date and time, such as "2026-10-03T08:05:00+00:00".
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Sat 3 Oct, 09:05" or "10月3日周六 09:05".
 */
export function dateTime(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { weekday: "short", day: "numeric", month: "short", hour: "2-digit",
    minute: "2-digit", hourCycle: "h23" }).format(new Date(value));
}

/**
 * Name a date briefly, for chips and labels.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Wed 23 Sep" or "9月23日周三".
 */
export function shortDate(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { weekday: "short", day: "numeric", month: "short" })
    .format(new Date(`${value}T12:00:00`));
}

/**
 * Name a date by its day and month alone, for a column or a list.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "7 Sept" or "9月7日".
 */
export function dayAndMonth(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

/**
 * Name a date by its weekday alone, briefly.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Thu" or "周四".
 */
export function weekdayOf(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { weekday: "short" }).format(new Date(`${value}T12:00:00`));
}

/**
 * Name a weekday by its number.
 * @param {number} index - 0 for Monday to 6 for Sunday.
 * @param {string} language - `en` or `zh`.
 * @param {"short"|"long"|"narrow"} [width="short"] - How fully it is named.
 * @returns {string} Such as "Mon", "Monday" or "周一".
 */
export function weekdayName(index, language, width = "short") {
  // 1 January 2024 was a Monday, so the weekday `index` days after it is the one asked for.
  return new Intl.DateTimeFormat(localeOf(language), { weekday: width }).format(new Date(2024, 0, 1 + index, 12));
}

/**
 * Read the local clock time of a stored moment, such as when a plan was set.
 * @param {string|null} value - An ISO timestamp.
 * @returns {string} Its HH:MM time in the Mac's local time, or an empty string without one.
 */
export function clockOfTimestamp(value) {
  return value ? new Date(value).toTimeString().slice(0, 5) : "";
}

/**
 * Read the local date of a stored moment.
 * @param {string} value - An ISO timestamp.
 * @returns {string} Its YYYY-MM-DD date in the Mac's local time.
 */
export function localDateOf(value) {
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** Minutes after midnight right now, in the Mac's local time. */
export function nowMinutes() {
  const now = new Date();
  return now.getHours() * 60 + now.getMinutes();
}
