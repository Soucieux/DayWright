/**
 * Catching up on several of a day's tasks at once, on Today's sheet or Ava's card: each task is left
 * as it is or given Done, Partly done or Skip, and one Save or Confirm applies them all.
 */

/** The choice that leaves a task as it is. */
export const AS_IS = "asIs";

/** The statuses a catch-up sets, in the order they are offered. */
const CAUGHT = ["done", "partial", "skipped"];

/** Each choice's words: a status's are the status controls' own, one set of words everywhere. */
export const CHOICE_KEYS = { [AS_IS]: "catchUpAsIs", done: "done", partial: "partial", skipped: "skipped" };

/** How long the notice of a save offers Undo. */
export const UNDO_SECONDS = 6;

/**
 * The choices a task offers: a task with a status shows it chosen, to change; one without may also be left as it is.
 * @param {{status: string}} task - A task as the service lists it to catch up on.
 * @returns {string[]} Its choices, in the order shown.
 */
export function choiceOptions(task) {
  return task.status === "planned" ? [AS_IS, ...CAUGHT] : CAUGHT;
}

/**
 * The choice each task starts with: the status Ava read for it, else the status it has, else as it is.
 * @param {{id: string, status: string, to?: string|null}[]} tasks - The day's tasks to catch up on.
 * @returns {Object<string, string>} The choice, by task id.
 */
export function firstChoices(tasks) {
  return Object.fromEntries(tasks.map((task) => [task.id, task.to || (task.status === "planned" ? AS_IS : task.status)]));
}

/**
 * The statuses one save sets: each task whose choice changes its status.
 * @param {{id: string, status: string}[]} tasks - The day's tasks to catch up on.
 * @param {Object<string, string>} choices - The choice, by task id.
 * @returns {Object<string, string>} The status to set, by task id.
 */
export function chosenStatuses(tasks, choices) {
  return Object.fromEntries(tasks
    .filter((task) => choices[task.id] && choices[task.id] !== AS_IS && choices[task.id] !== task.status)
    .map((task) => [task.id, choices[task.id]]));
}

/**
 * The words of the notice after a save, by how many tasks it updated.
 * @param {number} count - The tasks updated.
 * @returns {string} The message key.
 */
export function savedKey(count) {
  return count === 1 ? "catchUpUpdatedOne" : "catchUpUpdated";
}
