import { formatMinutes, fullDate } from "../time.js";

/**
 * How each kind of message the agents send through Ava is worded: an issue they found in the day,
 * a doubt about a change the user asked for, or a question about which task the user means. Each
 * returns the message key and its values from the notice's values.
 */
const NOTICE_WORDING = {
  slipping: (values, minutes) => ["avaNoticeSlipping",
    { title: values.taskTitle, unfinished: values.unfinished, latest: values.latest }],
  "length-off": (values, minutes) => (values.reason === "changing"
    ? ["avaNoticeLengthChanging", { title: values.taskTitle, minutes: minutes(values.minutes), changes: values.changes }]
    : ["avaNoticeLengthUnfinished", { title: values.taskTitle, minutes: minutes(values.minutes),
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
  "energy-short-review": (values, minutes) => ["energyNoteShortReview", { energy: values.energy, title: values.taskTitle }],
  "energy-harder-session": (values, minutes) => ["energyNoteHarderSession", { energy: values.energy, title: values.taskTitle }],
  "energy-heavy-load": (values, minutes) => ["energyNoteHeavyLoad", { energy: values.energy, minutes: minutes(values.minutes) }],
  "energy-biggest-work": (values, minutes) => ["energyNoteBiggestWork",
    { energy: values.energy, title: values.taskTitle, minutes: minutes(values.minutes) }],
  "energy-small-step": (values, minutes) => ["energyNoteSmallStep", { energy: values.energy, title: values.taskTitle }],
  "energy-next-big-step": (values, minutes) => ["energyNoteNextBigStep", { energy: values.energy, title: values.taskTitle }],
  "due-for-review": (values, minutes) => ["avaNoticeDueForReview", { title: values.goalTitle, days: values.days }],
  stalled: (values, minutes) => ["avaNoticeStalled", { title: values.goalTitle, days: values.days }],
  // An area agent's offer to change a length the user set to the time the task usually takes; its card goes with it.
  "usual-length": (values, minutes) => ["avaNoticeUsualLength",
    { title: values.taskTitle, usual: minutes(values.usualMinutes), set: minutes(values.setMinutes) }],
  // An area agent's offer, after a catch-up, to continue a partly done Learning task next session; its card goes with it.
  "continue-offer": (values, minutes) => ["avaNoticeContinueOffer", { title: values.taskTitle }],
  // The Learning agent's suggestion of Library items for a new Learn task made without one; its card goes with it.
  "link-offer": (values, minutes) => [values.count === 1 ? "avaNoticeLinkOfferOne" : "avaNoticeLinkOffer",
    { title: values.taskTitle, count: values.count }],
  // The notes and rules found in past conversations once they were condensed; its card, each one to keep ticked, goes with it.
  "memory-review": (values) => [values.count === 1 ? "avaNoticeMemoryReviewOne" : "avaNoticeMemoryReview", { count: values.count }],
  // What checking a connected folder's files found; its card, with each file to keep ticked, goes with it.
  "folder-check": (values, minutes) => ["avaNoticeFolderCheck",
    { title: values.title, ready: values.ready, unreadable: values.unreadable, notStudy: values.notStudy }],
  // Signals on an area's page that never change an estimate: a task often skipped, or often left without a status.
  "often-skipped": (values, minutes) => ["areaNoteOftenSkipped",
    { title: values.taskTitle, count: values.count, scheduled: values.scheduled }],
  "often-unanswered": (values, minutes) => ["areaNoteOftenUnanswered",
    { title: values.taskTitle, count: values.count, scheduled: values.scheduled }],
  "doubt-usual-time": (values, minutes) => ["avaDoubtUsualTime",
    { title: values.taskTitle, usual: values.usualStart, requested: values.requested, done: values.done }],
  // A usual finishing length is named only when it is longer than the one the task fell short at.
  "doubt-too-short": (values, minutes) => [values.doneMinutes > values.partialMinutes ? "avaDoubtTooShort" : "avaDoubtTooShortNoDone",
    { title: values.taskTitle, requested: minutes(values.requested), partial: values.partial,
      partialMinutes: minutes(values.partialMinutes), doneMinutes: values.doneMinutes == null ? null : minutes(values.doneMinutes) }],
  "clarify-task": (values, minutes) => (values.requested
    ? ["avaClarifyTaskTime", { time: values.requested }] : ["avaClarifyTaskLength", { minutes: minutes(values.minutes) }]),
  "clarify-past-task": (values, minutes, t, language) => ["avaClarifyPastTask", { date: fullDate(values.date, language) }],
  "clarify-repeat-scope": (values, minutes, t, language) => ["avaClarifyRepeatScope",
    { title: values.title, date: fullDate(values.date, language) }],
  "clarify-meal-scope": (values, minutes, t) => ["avaClarifyMealScope",
    { meal: t(values.meal === "dinner" ? "mealDinner" : "mealLunch"), range: `${values.start}–${values.end}` }],
  "clarify-which": (values, minutes, t) => ["avaClarifyWhich", {
    tasks: values.tasks.map((task) => (task.start ? t("avaClarifyTaskAt", { title: task.title, time: task.start })
      : t("avaClarifyTaskUntimed", { title: task.title }))).join(t("listSeparator")) }],
};

/**
 * Word one of Ava's messages about an issue in the interface language.
 * @param {{kind: string, values: object}} notice - The message as the local service returns it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`, for the minutes and dates.
 * @returns {string} The message, or nothing for a kind this interface doesn't know.
 */
export function noticeText(notice, t, language) {
  const wording = NOTICE_WORDING[notice.kind];
  if (!wording) return "";
  const [key, values] = wording(notice.values, (minutes) => formatMinutes(minutes, language), t, language);
  return t(key, values);
}

/**
 * Ava's log: the conversation, with its messages about issues placed by when each was made, and a
 * mark wherever the conversation turns to another day. A message still being sent has no time yet
 * and stays last.
 * @param {object[]} messages - The conversation, oldest first; each saved one has `created_at`, and
 *   `topicDate`, the day it was about, unless it was saved before messages kept one.
 * @param {object[]} notices - Ava's messages about issues, each with `createdAt` and its `group`.
 * @returns {{key: string, message?: object, notice?: object, offers?: object[], topic?: string}[]} Each
 *   entry, oldest first, with a `topic` entry naming the new day before the first message about it; the
 *   agents' offers that arrive together, with nothing between them, as one entry of `offers`. A
 *   reminder, which Today shows and never Ava's chat, and a notice of a kind this interface doesn't
 *   know are left out.
 */
export function talkLog(messages, notices) {
  const entries = [
    ...messages.map((message) => ({ key: message.id, message, at: message.created_at })),
    ...notices.filter((notice) => NOTICE_WORDING[notice.kind] && notice.group !== "reminder")
      .map((notice) => ({ key: notice.id, notice, at: notice.createdAt })),
  ];
  const ordered = entries
    .map((entry, index) => ({ entry, index }))
    .sort((first, second) => compareTimes(first.entry.at, second.entry.at) || first.index - second.index)
    .map(({ entry: { at, ...entry } }) => entry);
  let topic = null;
  const dated = ordered.flatMap((entry) => {
    const day = entry.message?.topicDate;
    if (!day) return [entry];
    const turned = topic !== null && day !== topic;
    topic = day;
    return turned ? [{ key: `topic-${entry.key}`, topic: day }, entry] : [entry];
  });
  return dated.reduce((log, entry) => {
    const last = log.at(-1);
    if (entry.notice?.group !== "offer") return [...log, entry];
    if (last?.offers) return [...log.slice(0, -1), { ...last, offers: [...last.offers, entry.notice] }];
    return [...log, { key: `offers-${entry.key}`, offers: [entry.notice] }];
  }, []);
}

/** Order two ISO times, a missing one after every other. */
function compareTimes(first, second) {
  if (first === second) return 0;
  if (!first) return 1;
  if (!second) return -1;
  return first < second ? -1 : 1;
}
