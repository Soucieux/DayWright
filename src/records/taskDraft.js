import { formatMinutes } from "../time.js";

/**
 * The shortest length a user gives a task, in minutes, in the form or through Ava. A task saved
 * without a length gets an estimate from its area agent instead.
 */
export const MIN_TASK_MINUTES = 30;

/** The start time offered when a task is made fixed and has none yet. */
const NEW_TASK_START = "09:00";

/**
 * Choose the date a new task starts on: the day on show when that is later than today, otherwise
 * today, since past days are read-only.
 * @param {string} shownDate - The YYYY-MM-DD day on show.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {string} The new task's date.
 */
export function newTaskDate(shownDate, today) {
  return shownDate > today ? shownDate : today;
}

/**
 * Turn a stored task into editable fields, or start a blank task for a date.
 * @param {object|null} item - The stored task, or null for a new one.
 * @param {string} date - The date a new task belongs to.
 * @param {string} [domain="life"] - The area a new task starts in.
 * @param {string} [goalId=""] - A goal a new task starts linked to.
 * @returns {object} Form fields. A flexible task keeps a start time in the form only so that
 *   switching it to fixed offers one; `taskPayload` drops it. The length is blank until the user
 *   gives one, so a length an agent estimated stays an estimate when the task is saved again. The
 *   status is not a form field: a saved task keeps the outcome reported for it.
 */
export function taskDraft(item, date, domain = "life", goalId = "") {
  return item ? {
    date: item.date, title: item.title, detail: item.detail, domain: item.domain,
    startTime: item.start_time || NEW_TASK_START,
    durationMinutes: item.durationSource === "estimate" ? "" : item.duration_minutes,
    constraintKind: item.constraint_kind, repeatKind: item.repeatKind,
    goalId: item.goalId || "",
  } : {
    date, title: "", detail: "", domain, startTime: NEW_TASK_START,
    durationMinutes: "", constraintKind: "flexible", repeatKind: "none",
    goalId,
  };
}

/**
 * Shape form fields into the task the local service stores. Only a fixed task has a start time;
 * a plan places a flexible one. A blank length is sent as none, for the area agent to estimate.
 * @param {object} draft - Form fields from `taskDraft`.
 * @returns {object} The payload for creating or updating a task.
 */
export function taskPayload(draft) {
  return {
    ...draft, startTime: draft.constraintKind === "fixed" ? draft.startTime : null,
    goalId: draft.goalId || null,
    durationMinutes: draft.durationMinutes === "" ? null : Number(draft.durationMinutes),
  };
}

/**
 * Word a row's length, marked "≈" when its area agent estimated it rather than the user giving it.
 * @param {{duration_minutes: number, durationSource?: string, source?: object}} row - A task, or a
 *   plan entry carrying its task as `source`.
 * @param {string} language - `en` or `zh`.
 * @returns {string} The length, such as "≈ 40 min".
 */
export function taskLength(row, language) {
  const estimated = (row.source || row).durationSource === "estimate";
  return `${estimated ? "≈ " : ""}${formatMinutes(row.duration_minutes, language)}`;
}

/**
 * The goals a task in one area may link to: active goals in that same area, and the goal it is
 * already in, even while that one is paused or completed.
 * @param {object[]} goals - The user's goals.
 * @param {string} domain - The task's area.
 * @param {string} [keepId=""] - The goal the task is already in.
 * @returns {object[]} The goals it can link to.
 */
export function linkableGoals(goals, domain, keepId = "") {
  return goals.filter((goal) => goal.domain === domain && (goal.status === "active" || goal.id === keepId));
}
