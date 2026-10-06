import { formatMinutes, fullDate } from "../time.js";

/**
 * How each kind of message the agents send through Ava is worded: an issue they found in the day,
 * a doubt about a change the user asked for, or a question about which task the user means. Each
 * returns the message key and its values from the notice's values.
 */
const NOTICE_WORDING = {
  slipping: (values, minutes, name) => ["avaNoticeSlipping",
    { title: name(values.taskTitle), unfinished: values.unfinished, latest: values.latest }],
  "length-off": (values, minutes, name) => (values.reason === "changing"
    ? ["avaNoticeLengthChanging", { title: name(values.taskTitle), minutes: minutes(values.minutes), changes: values.changes }]
    : ["avaNoticeLengthUnfinished", { title: name(values.taskTitle), minutes: minutes(values.minutes),
      partial: values.partial, reported: values.reported }]),
  // With no free time left at all, it says so rather than "only 0 min is free".
  "day-wont-fit": (values, minutes) => (values.freeMinutes > 0
    ? ["avaNoticeDayWontFit", { count: values.count, taskMinutes: minutes(values.taskMinutes), freeMinutes: minutes(values.freeMinutes) }]
    : ["avaNoticeDayWontFitNoTime", { taskMinutes: minutes(values.taskMinutes) }]),
  // Low energy alone is never posted to Ava; Life's notes show it.
  "low-energy": (values) => ["avaNoticeLowEnergy", { energy: values.energy }],
  "low-energy-full": (values, minutes) => ["avaNoticeLowEnergyFull",
    { energy: values.energy, taskMinutes: minutes(values.taskMinutes), freeMinutes: minutes(values.freeMinutes) }],
  // Each area's note on the day's average energy; they show on its page and never reach Ava.
  "energy-short-review": (values, minutes, name) => ["energyNoteShortReview", { energy: values.energy, title: name(values.taskTitle) }],
  "energy-harder-session": (values, minutes, name) => ["energyNoteHarderSession", { energy: values.energy, title: name(values.taskTitle) }],
  "energy-heavy-load": (values, minutes) => ["energyNoteHeavyLoad", { energy: values.energy, minutes: minutes(values.minutes) }],
  "energy-biggest-work": (values, minutes, name) => ["energyNoteBiggestWork",
    { energy: values.energy, title: name(values.taskTitle), minutes: minutes(values.minutes) }],
  "energy-small-step": (values, minutes, name) => ["energyNoteSmallStep", { energy: values.energy, title: name(values.taskTitle) }],
  "energy-next-big-step": (values, minutes, name) => ["energyNoteNextBigStep", { energy: values.energy, title: name(values.taskTitle) }],
  "due-for-review": (values, minutes, name) => ["avaNoticeDueForReview", { title: name(values.goalTitle), days: values.days }],
  stalled: (values, minutes, name) => ["avaNoticeStalled", { title: name(values.goalTitle), days: values.days }],
  "doubt-usual-time": (values, minutes, name) => ["avaDoubtUsualTime",
    { title: name(values.taskTitle), usual: values.usualStart, requested: values.requested, done: values.done }],
  // A usual finishing length is named only when it is longer than the one the task fell short at.
  "doubt-too-short": (values, minutes, name) => [values.doneMinutes > values.partialMinutes ? "avaDoubtTooShort" : "avaDoubtTooShortNoDone",
    { title: name(values.taskTitle), requested: minutes(values.requested), partial: values.partial,
      partialMinutes: minutes(values.partialMinutes), doneMinutes: values.doneMinutes == null ? null : minutes(values.doneMinutes) }],
  "clarify-task": (values, minutes) => (values.requested
    ? ["avaClarifyTaskTime", { time: values.requested }] : ["avaClarifyTaskLength", { minutes: minutes(values.minutes) }]),
  "clarify-past-task": (values, minutes, name, t, language) => ["avaClarifyPastTask", { date: fullDate(values.date, language) }],
  "clarify-repeat-scope": (values, minutes, name, t, language) => ["avaClarifyRepeatScope",
    { title: name(values.title), date: fullDate(values.date, language) }],
  "clarify-meal-scope": (values, minutes, name, t) => ["avaClarifyMealScope",
    { meal: t(values.meal === "dinner" ? "mealDinner" : "mealLunch"), range: `${values.start}–${values.end}` }],
  "clarify-which": (values, minutes, name, t) => ["avaClarifyWhich", {
    tasks: values.tasks.map((task) => (task.start ? t("avaClarifyTaskAt", { title: name(task.title), time: task.start })
      : t("avaClarifyTaskUntimed", { title: name(task.title) }))).join(t("listSeparator")) }],
};

/**
 * Word one of Ava's messages about an issue in the interface language.
 * @param {{kind: string, values: object}} notice - The message as the local service returns it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`, for the minutes and dates.
 * @param {(title: string) => string} [name] - Shows a task's title, as the demo workspace translates it.
 * @returns {string} The message, or nothing for a kind this interface doesn't know.
 */
export function noticeText(notice, t, language, name = (title) => title) {
  const wording = NOTICE_WORDING[notice.kind];
  if (!wording) return "";
  const [key, values] = wording(notice.values, (minutes) => formatMinutes(minutes, language), name, t, language);
  return t(key, values);
}

/**
 * Ava's log: the conversation, with its messages about issues placed by when each was made, and a
 * mark wherever the conversation turns to another day. A message still being sent has no time yet
 * and stays last.
 * @param {object[]} messages - The conversation, oldest first; each saved one has `created_at`, and
 *   `topicDate`, the day it was about, unless it was saved before messages kept one.
 * @param {object[]} notices - Ava's messages about issues, each with `createdAt`.
 * @returns {{key: string, message?: object, notice?: object, topic?: string}[]} Each entry, oldest
 *   first, with a `topic` entry naming the new day before the first message about it; a notice of a
 *   kind this interface doesn't know is left out.
 */
export function talkLog(messages, notices) {
  const entries = [
    ...messages.map((message) => ({ key: message.id, message, at: message.created_at })),
    ...notices.filter((notice) => NOTICE_WORDING[notice.kind]).map((notice) => ({ key: notice.id, notice, at: notice.createdAt })),
  ];
  const ordered = entries
    .map((entry, index) => ({ entry, index }))
    .sort((first, second) => compareTimes(first.entry.at, second.entry.at) || first.index - second.index)
    .map(({ entry: { at, ...entry } }) => entry);
  let topic = null;
  return ordered.flatMap((entry) => {
    const day = entry.message?.topicDate;
    if (!day) return [entry];
    const turned = topic !== null && day !== topic;
    topic = day;
    return turned ? [{ key: `topic-${entry.key}`, topic: day }, entry] : [entry];
  });
}

/** Order two ISO times, a missing one after every other. */
function compareTimes(first, second) {
  if (first === second) return 0;
  if (!first) return 1;
  if (!second) return -1;
  return first < second ? -1 : 1;
}
