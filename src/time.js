/** Minutes in a day, for wrapping times past midnight. */
const MINUTES_PER_DAY = 24 * 60;

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
 * @returns {string} The range, such as `17:30–18:00`.
 */
export function timeRange(start, durationMinutes) {
  return `${start}–${clockOf(minutesOf(start) + durationMinutes)}`;
}

/**
 * Format a length of time the way the interface reads it aloud: "45 min", "1 h", "3 h 30".
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
  return rest ? `${hours} h ${rest}` : `${hours} h`;
}

/**
 * Name a date's weekday and its day and month, for page headings.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {{weekday: string, dayMonth: string}} Such as "Wednesday" and "23 September".
 */
export function longDate(value, language) {
  const date = new Date(`${value}T12:00:00`);
  const locale = language === "zh" ? "zh-Hans" : "en-GB";
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
  const date = new Date(`${value}T12:00:00`);
  const locale = language === "zh" ? "zh-Hans" : "en-GB";
  return new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(date);
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
