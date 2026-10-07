import { formatMinutes } from "../time.js";

/** The view the desktop session opens for the menu bar's panel: `PANEL_VIEW` in backend/app/desktop.py. */
export const PANEL_VIEW = "menubar";

/**
 * Whether a window's address asks for the menu bar's panel rather than the workbench.
 * @param {string} search - The address's query, such as "?view=menubar".
 * @returns {boolean} True for the panel's view.
 */
export function isPanelView(search) {
  return new URLSearchParams(search).get("view") === PANEL_VIEW;
}

/**
 * The address through which the panel asks the desktop shell for something; the shell answers it and
 * the panel stays where it is.
 * @param {"open"|"refresh"} request - Open DayWright's window, or renew the menu bar's title.
 * @returns {string} Such as "daywright://open".
 */
export function shellAddress(request) {
  return `daywright://${request}`;
}

/**
 * Ask the desktop shell for something, when the panel runs in it; anywhere else nothing happens.
 * @param {"open"|"refresh"} request - See {@link shellAddress}.
 */
export function askShell(request) {
  if (window.daywrightShell === PANEL_VIEW) window.location.href = shellAddress(request);
}

/**
 * The two facts the panel gives under a task's title: the time the current task has taken, or when
 * the next one starts; and its set time, with whose it is.
 * @param {{start: string|null, minutes: number, durationSource: string}} task - The task from /api/now.
 * @param {number|null} taken - The minutes the current task has taken, or null for the next task.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {"en"|"zh"} language - The interface language.
 * @returns {string[]} Such as ["32 min taken", "1 h, you set"] or ["Untimed", "45 min, estimated"].
 */
export function taskFacts(task, taken, t, language) {
  const when = taken === null ? task.start || t("untimed") : t("menubarTaken", { minutes: formatMinutes(taken, language) });
  return [when, t(task.durationSource === "user" ? "setByYou" : "setByAgent", { minutes: formatMinutes(task.minutes, language) })];
}
