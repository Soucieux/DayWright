/**
 * The day's tasks that are paused with their goal. A task is never paused on its own.
 * @param {object[]} dayItems - The day's tasks, each with the `goalStatus` of its goal, if any.
 * @returns {Set<string>} Their ids.
 */
export function pausedIds(dayItems) {
  return new Set(dayItems.filter((item) => item.goalStatus === "paused").map((item) => item.id));
}

/**
 * A plan's tasks that are paused with their goal: those it still holds, because it was made before
 * the pause, and those it leaves out. A plan made after the pause holds none.
 * @param {object[]} entries - The plan's entries, each with the `source_item_id` it schedules.
 * @param {object[]} dayItems - The day's tasks, each with its goal's `goalStatus`.
 * @returns {{held: object[], left: object[]}} The entries for paused tasks, and the paused tasks
 *   no entry schedules.
 */
export function pausedInPlan(entries, dayItems) {
  const paused = pausedIds(dayItems);
  const scheduled = new Set(entries.map((entry) => entry.source_item_id));
  return {
    held: entries.filter((entry) => paused.has(entry.source_item_id)),
    left: dayItems.filter((item) => paused.has(item.id) && !scheduled.has(item.id)),
  };
}
