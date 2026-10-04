import { formatMinutes, fullDate, timeRange } from "../time.js";

/** The label each field a past task's edit can change goes by. */
const FIELD_LABELS = {
  title: "fieldTitle", detail: "fieldDetail", domain: "fieldArea", goalId: "fieldGoal", date: "fieldDate",
  startTime: "fieldStart", durationMinutes: "fieldLength", status: "fieldStatus",
};

/**
 * Word one change an edit makes to a past task, as "Start: 09:00 → 10:00".
 * @param {{field: string, from: *, to: *}} change - The field and its value before and after.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @param {{id: string, title: string}[]} goals - Every goal, to name a linked one.
 * @param {(title: string) => string} [name] - Shows a title, as the demo workspace translates it.
 * @returns {string} The change, before → after.
 */
export function changeLine({ field, from, to }, t, language, goals, name = (title) => title) {
  const shown = (value) => {
    if (field === "domain") return t(value);
    if (field === "goalId") return value ? name(goals.find((goal) => goal.id === value)?.title ?? "") : t("noGoalOption");
    if (field === "date") return fullDate(value, language);
    if (field === "startTime") return value || t("noStartTime");
    if (field === "durationMinutes") return formatMinutes(value, language);
    if (field === "status") return t(value);
    return value ? `“${name(value)}”` : t("noneValue");
  };
  return t("proposalFieldLine", { field: t(FIELD_LABELS[field]), from: shown(from), to: shown(to) });
}

/**
 * Read what a proposed change would do, from the proposal and the day it belongs to.
 * @param {{actionType: string, payload: object}} proposal - A change the agents proposed.
 * @param {{id: string, title: string, duration_minutes: number}[]} dayItems - The tasks of the day on show.
 * @returns {object} `kind` is `set` (set a plan: `to`), `replace` (replace the set plan: `from`,
 *   `to`), `shorten` (shorten a future task: `title`, `from` and `to` in minutes, with `title` and
 *   `from` null when the task isn't on the day on show), `move` (move a task: `title`, `from` and
 *   `to` as HH:MM, `from` null when it has no start time), `length` (give a task any length:
 *   `title`, `from` and `to` in minutes, as for `shorten`), `edit` (change a past task: `title`,
 *   and `changes`, each a `field` with its value `from` and `to`), `remove` (remove a past task:
 *   `title`, `start`, null when it has none, `minutes`, and `keptByPlan`, true when the plan set
 *   for its day keeps its entry), `meal` (move lunch or dinner: its `title`, its `scope`,
 *   `standing` from `date` on or one `day`, its times `from` and `to` as "HH:MM–HH:MM", and
 *   `planChanges`, true when today's set plan changes around it) or `other`; each carries its `date`.
 */
export function proposalView(proposal, dayItems) {
  const { actionType, payload } = proposal;
  if (actionType === "change_meal") {
    return { kind: "meal", date: payload.date, title: payload.title, scope: payload.scope,
      from: timeRange(payload.before.start, payload.before.minutes), to: timeRange(payload.start, payload.minutes),
      planChanges: payload.planChanges };
  }
  if (actionType === "edit_item") {
    return { kind: "edit", date: payload.date, title: payload.title, changes: Object.entries(payload.changes)
      .map(([field, to]) => ({ field, from: payload.before[field] ?? null, to })) };
  }
  if (actionType === "remove_item") {
    return { kind: "remove", date: payload.date, title: payload.title, start: payload.startTime, minutes: payload.durationMinutes,
      keptByPlan: Boolean(payload.inSetPlan) };
  }
  if (actionType === "select_variant") {
    return payload.reviewedFromVariantName
      ? { kind: "replace", date: payload.date, from: payload.reviewedFromVariantName, to: payload.variantName }
      : { kind: "set", date: payload.date, to: payload.variantName };
  }
  if (actionType === "shorten_future_item") {
    const item = dayItems.find((entry) => entry.id === payload.itemId);
    return { kind: "shorten", date: payload.date, title: item?.title ?? null, from: item?.duration_minutes ?? null, to: payload.durationMinutes };
  }
  if (actionType === "set_length") {
    const item = dayItems.find((entry) => entry.id === payload.itemId);
    return { kind: "length", date: payload.date, title: item?.title ?? null, from: item?.duration_minutes ?? null, to: payload.durationMinutes };
  }
  if (actionType === "move_item") {
    const item = dayItems.find((entry) => entry.id === payload.itemId);
    return { kind: "move", date: payload.date, title: item?.title ?? null, from: item?.start_time ?? null, to: payload.startTime };
  }
  return { kind: "other", date: payload?.date ?? null };
}
