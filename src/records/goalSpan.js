import { clockOfTimestamp, dateTime, localDateOf } from "../time.js";

/**
 * Say the time a goal spans: from when it was made to that plus the length of every task in it,
 * given or estimated. Nobody sets it by hand; adding a task extends it. A span within one day names
 * that day once.
 * @param {{startAt: string, endAt: string}} goal - The goal as the local service returns it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Sat 3 Oct, 09:00 – 10:45", or "From Sat 3 Oct, 09:00 to Sun 4 Oct, 10:45".
 */
export function goalSpan(goal, t, language) {
  if (localDateOf(goal.startAt) === localDateOf(goal.endAt)) {
    return t("goalSpanSameDay", { from: dateTime(goal.startAt, language), to: clockOfTimestamp(goal.endAt) });
  }
  return t("goalSpan", { from: dateTime(goal.startAt, language), to: dateTime(goal.endAt, language) });
}
