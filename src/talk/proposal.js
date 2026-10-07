import { formatMinutes, fullDate, shortDate, timeRange } from "../time.js";

/**
 * Name the day a card's change is on: today and tomorrow in words, with no "on" before them, and
 * any other day by its short date, with "on" before it where the language uses one.
 * @param {string} date - The YYYY-MM-DD day.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {{on: string, plain: string}} The day as a title's `{when}` takes it, and on its own.
 */
export function cardDay(date, today, t, language) {
  const tomorrow = new Date(Date.parse(`${today}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);
  const word = date === today ? t("todayWord") : date === tomorrow ? t("tomorrowWord") : null;
  if (word) return { on: word, plain: word };
  const plain = shortDate(date, language);
  return { on: t("onDay", { date: plain }), plain };
}

/**
 * A new task as a card reads it from the proposal.
 * @param {{title: string, date: string, startTime: string|null, durationMinutes: number|null, repeatKind: string}} task
 * @returns {{title: string, date: string, start: string|null, minutes: number|null, repeat: string}} The task.
 */
function newTask(task) {
  // A length its source estimated, as a learning task's follow-up carries, is the task's length too.
  return { title: task.title, date: task.date, start: task.startTime, minutes: task.durationMinutes ?? task.estimateMinutes ?? null,
    repeat: task.repeatKind };
}

/**
 * Word a new task Ava proposes on one line: its title, day, start, length and repeat.
 * @param {{title: string, date: string, start: string|null, minutes: number|null, repeat: string}} task - As proposalView reads it.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "“Read chapter 4” · tomorrow · 09:00 · 45 min · repeats daily".
 */
export function newTaskLine(task, today, t, language) {
  const parts = [`“${task.title}”`, cardDay(task.date, today, t, language).plain, task.start || t("untimed"),
    task.minutes ? formatMinutes(task.minutes, language) : t("proposalLengthByAgent")];
  if (task.repeat !== "none") parts.push(t("proposalNewTaskRepeats", { kind: t(task.repeat === "weekly" ? "repeatWeekly" : "repeatDaily") }));
  return parts.join(" · ");
}

/** The label each field a past task's edit can change goes by. */
const FIELD_LABELS = {
  title: "fieldTitle", detail: "fieldDetail", domain: "fieldArea", goalId: "fieldGoal", date: "fieldDate",
  startTime: "fieldStart", durationMinutes: "fieldLength", status: "fieldStatus", actualTime: "fieldActualTime",
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
  // A time confirmed has no before and after: it now counts as it is.
  if (field === "timeConfirmed") return t("proposalTimeConfirmed");
  const shown = (value) => {
    if (field === "actualTime") return value?.start ? `${value.start}–${value.end}` : t("noTimeKept");
    if (field === "domain") return t(value);
    if (field === "goalId") return value ? name(goals.find((goal) => goal.id === value)?.title ?? "") : t("noGoalOption");
    if (field === "date") return fullDate(value, language);
    if (field === "startTime") return value || t("untimed");
    if (field === "durationMinutes") return formatMinutes(value, language);
    if (field === "status") return t(value);
    return value ? `“${name(value)}”` : t("noneValue");
  };
  return t("proposalFieldLine", { field: t(FIELD_LABELS[field]), from: shown(from), to: shown(to) });
}

/**
 * Say what a past task's change left out, as on its past day a task keeps its place.
 * @param {string[]} fields - The fields left out: "date", "startTime" or "durationMinutes".
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Left out: length. On its past day a task keeps its place."
 */
export function leftOutLine(fields, t, language) {
  return t("proposalLeftOut", { fields: fields.map((field) => t(FIELD_LABELS[field]).toLowerCase())
    .join(language === "zh" ? "、" : ", ") });
}

/**
 * Read what a proposed change would do, from the proposal and the day it belongs to.
 * @param {{actionType: string, payload: object}} proposal - A change the agents proposed.
 * @param {{id: string, title: string, duration_minutes: number}[]} dayItems - The tasks of the day on show.
 * @returns {object} `kind` is `set` (set a plan: `to`), `replace` (replace the set plan: `from`,
 *   `to`), `shorten` (shorten a future task: `title`, `from` and `to` in minutes, with `title` and
 *   `from` null when the task isn't on the day on show), `move` (move a task: `title`, `from` and
 *   `to` as HH:MM, `from` null when it has no start time), `length` (give a task any length:
 *   `title`, `from` and `to` in minutes, as for `shorten`), `usual` (give a task the length its done times
 *   usually take, on its `days` to come from `date`: `title`, `from` and `to` in minutes), `edit` (change a past task: `title`,
 *   and `changes`, each a `field` with its value `from` and `to`, with the `days` it changes when
 *   the task repeats and the fields it `leftOut` as a past task keeps its place), `repeat` (start, stop or switch a repeat from a past day: `title`, `mode`
 *   `start`, `stop` or `switch`, `repeatKind`, the first day it changes on, `startsOn`, and the days
 *   still to do it `removes`),
 *   `addTask` (a new task: its `task`, the `goalTitle` it joins or null, and its area, `domain`, with
 *   what chose it, `domainSource`: "goal", "message", "model" or "keywords"; a learning task's
 *   follow-up also has what it `continues`: the earlier task's `date` and the items `left`), `tick`
 *   (tick or untick a checklist item: the task's `title`, the `item`, and whether it is `done`), `addGoal` (a new goal:
 *   its `title`, `domain`, `domainSource` and first `tasks`),
 *   `remove` (remove a past task:
 *   `title`, `start`, null when it has none, `minutes`, and `keptByPlan`, true when the plan set
 *   for its day keeps its entry), `meal` (move lunch or dinner: its `title`, its `scope`,
 *   `standing` from `date` on or one `day`, its times `from` and `to` as "HH:MM–HH:MM",
 *   `planChanges`, true when today's set plan changes around it, and `replaces`, the one-day times
 *   a standing move replaces, each its `date` and `range`), `energy` (add a reading to today's
 *   energy: its `level`, and today's average `before`, null with no reading yet, and `after` it) or
 *   `other`; each carries its `date`.
 */
export function proposalView(proposal, dayItems) {
  const { actionType, payload } = proposal;
  if (actionType === "set_energy") {
    return { kind: "energy", date: payload.date, level: payload.level, before: payload.before, after: payload.after };
  }
  if (actionType === "change_meal") {
    return { kind: "meal", date: payload.date, title: payload.title, scope: payload.scope,
      from: timeRange(payload.before.start, payload.before.minutes), to: timeRange(payload.start, payload.minutes),
      planChanges: payload.planChanges,
      replaces: (payload.replaces || []).map((other) => ({ date: other.date, range: timeRange(other.start, other.minutes) })) };
  }
  if (actionType === "edit_item") {
    return { kind: "edit", date: payload.date, title: payload.title, changes: Object.entries(payload.changes)
      .map(([field, to]) => ({ field, from: payload.before[field] ?? null, to })),
    ...(payload.days ? { days: payload.days } : {}), ...(payload.leftOut ? { leftOut: payload.leftOut } : {}) };
  }
  if (actionType === "add_item") {
    return { kind: "addTask", date: payload.date, goalTitle: payload.goalTitle || null, domain: payload.domain,
      domainSource: payload.domainSource, task: newTask(payload),
      ...(payload.continues ? { continues: { date: payload.continues.date, left: payload.left || [] } } : {}) };
  }
  if (actionType === "tick_item") {
    return { kind: "tick", date: payload.date, title: payload.title, item: payload.entryTitle, done: payload.done };
  }
  if (actionType === "add_goal") {
    return { kind: "addGoal", date: payload.date, title: payload.title, domain: payload.domain,
      domainSource: payload.domainSource, tasks: payload.tasks.map(newTask) };
  }
  if (actionType === "repeat_item") {
    return { kind: "repeat", date: payload.date, title: payload.title, mode: payload.mode, repeatKind: payload.repeatKind,
      startsOn: payload.startsOn, removes: payload.removes || [] };
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
  if (actionType === "usual_length") {
    return { kind: "usual", date: payload.date, title: payload.title, from: payload.fromMinutes, to: payload.durationMinutes,
      days: payload.itemIds.length };
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
