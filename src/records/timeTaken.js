import { minutesOf } from "../time.js";

/**
 * A time a task took of this many times its length or more, as a task stopped at its limit took, is one to
 * check: `CHECK_TIME_FACTOR` in backend/app/database.py.
 */
export const CHECK_TIME_FACTOR = 2;

/** Each reason Today's notice gives for one of yesterday's tasks, by the reason the local service names. */
const YESTERDAY_REASONS = { noReply: "yesterdayNoReply", limit: "yesterdayLimit", checkTime: "yesterdayCheckTime",
  dayPaused: "yesterdayDayPaused" };

/**
 * The time a task actually took, which its status set: its first stretch's start and its last one's
 * stop, its minutes (every stretch it was current added up, or from start to stop for a time kept
 * before those were), and whether it is a time to check, over CHECK_TIME_FACTOR times its length and
 * not yet confirmed.
 * @param {{duration_minutes: number, actualStart?: string|null, actualEnd?: string|null, actualMinutes?: number|null,
 *   timeConfirmed?: boolean, source?: object}} row - A task, or a plan entry carrying its task as `source`.
 * @returns {{start: string, end: string, minutes: number, toCheck: boolean}|null} The time, or null when none was kept.
 */
export function timeTaken(row) {
  const task = row.source || row;
  if (!task.actualStart || !task.actualEnd) return null;
  const minutes = task.actualMinutes ?? minutesOf(task.actualEnd) - minutesOf(task.actualStart);
  return { start: task.actualStart, end: task.actualEnd, minutes,
    toCheck: minutes >= CHECK_TIME_FACTOR * row.duration_minutes && !task.timeConfirmed };
}

/**
 * The time spent on a task, which every status counts: the time it took, nothing for a time to check
 * until it is confirmed, and for a task done or partly done before times were kept, its length.
 * @param {object} row - A task, or a plan entry with its task; see `timeTaken`.
 * @returns {number} Minutes.
 */
export function spentMinutes(row) {
  const taken = timeTaken(row);
  if (taken) return taken.toCheck ? 0 : taken.minutes;
  return ["done", "partial"].includes(row.completion_status) ? row.duration_minutes : 0;
}

/**
 * Which "Not done" a task reads, left without a status once its day's 22:00 passed, as the local service
 * marks it: "Not done · no reply", or "Not done · paused" on a day that ended paused.
 * @param {{noReply?: boolean, dayPaused?: boolean, source?: object}} row - A task, or a plan entry with its task.
 * @returns {"noReply"|"dayPaused"|false} The reading, or false for neither.
 */
export function noReplyOf(row) {
  const task = row.source || row;
  return task.dayPaused ? "dayPaused" : task.noReply ? "noReply" : false;
}

/**
 * What Today's notice says about yesterday: how many tasks need a word, when the day was paused if it ended
 * paused, and for each task, why.
 * @param {{pausedAt?: string|null, tasks: {title: string, reason: string}[]}} notice - The notice from the local service.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {(title: string) => string} [name] - Shows a task's title, as the demo workspace translates it.
 * @returns {{title: string, paused: string|null, tasks: string[]}} The notice's heading, its paused line, and a
 *   line for each task.
 */
export function yesterdayLines(notice, t, name = (title) => title) {
  return { title: t("yesterdayNoticeTitle", { count: notice.tasks.length }),
    // When the day was paused goes with the tasks it left not done · paused.
    paused: notice.pausedAt && notice.tasks.some((task) => task.reason === "dayPaused") ? t("yesterdayPausedAt", { time: notice.pausedAt }) : null,
    tasks: notice.tasks.map((task) => t("yesterdayTaskLine", { title: name(task.title), reason: t(YESTERDAY_REASONS[task.reason]) })) };
}
