/** How many reminders Today shows before "+ N more" opens the rest in place. */
export const REMINDERS_SHOWN = 3;

/** One day in milliseconds, to count a reminder's age in days. */
const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Each kind of reminder the agents raise about the day: its short form on Today, and the one thing to do about it
 * beside Dismiss (none for low energy, which Dismiss alone answers).
 */
const REMINDERS = {
  slipping: { key: "reminderSlipping", action: "seeTasks" },
  "length-off": { key: "reminderLengthOff", action: "changeLength" },
  "day-wont-fit": { key: "reminderDayWontFit", action: "comparePlans" },
  "low-energy": { key: "reminderLowEnergy", action: null },
  "low-energy-full": { key: "reminderLowEnergyFull", action: null },
  "due-for-review": { key: "reminderDueForReview", action: "planSession" },
  stalled: { key: "reminderStalled", action: "addStep" },
};

/** Each action's button. */
export const REMINDER_ACTIONS = {
  seeTasks: "reminderSeeTasks",
  changeLength: "reminderChangeLength",
  comparePlans: "reminderComparePlans",
  planSession: "reminderPlanSession",
  addStep: "reminderAddStep",
};

/**
 * A reminder as Today lists it.
 * @param {{kind: string, values: object, since: string}} reminder - As the local service gives it, with the day its
 *   issue first came up.
 * @param {string} today - YYYY-MM-DD.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {{text: string, since: string, action: string|null}|null} Its short form, its age in words and its action
 *   (see REMINDER_ACTIONS); null for a kind that is no reminder.
 */
export function reminderLine(reminder, today, t) {
  const kind = REMINDERS[reminder.kind];
  if (!kind) return null;
  const title = reminder.values.taskTitle || reminder.values.goalTitle || "";
  const days = Math.max(0, Math.round((Date.parse(today) - Date.parse(reminder.since || today)) / DAY_MS));
  const since = days === 0 ? t("reminderSinceToday")
    : days === 1 ? t("reminderSinceOneDay") : t("reminderSinceDays", { count: days });
  return { text: t(kind.key, { title }), since, action: kind.action };
}
