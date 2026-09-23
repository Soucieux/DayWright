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

/** Minutes after midnight right now, in the Mac's local time. */
export function nowMinutes() {
  const now = new Date();
  return now.getHours() * 60 + now.getMinutes();
}
