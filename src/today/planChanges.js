/**
 * Compare a set plan's entries with the tasks they came from: which tasks the plan placed, moved
 * or resized, which it left as they were, and which of the day's tasks it doesn't hold.
 * @param {object[]} entries - The set plan's entries, each naming its task in `source_item_id`.
 * @param {object[]} tasks - The day's tasks.
 * @returns {{changed: {entry: object, task: object, placed: boolean, moved: boolean, resized: boolean}[], kept: object[], missing: object[]}}
 *   The changed entries with their tasks and what changed, the entries kept as their tasks were,
 *   and the accepted tasks no entry holds, such as ones added after the plan was set.
 */
export function planChanges(entries, tasks) {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  const compared = entries.map((entry) => {
    const task = byId.get(entry.source_item_id);
    if (!task) return { entry, task: null, placed: false, moved: false, resized: false };
    return {
      entry, task,
      placed: !task.start_time,
      moved: Boolean(task.start_time) && task.start_time !== entry.start_time,
      resized: task.duration_minutes !== entry.duration_minutes,
    };
  });
  const held = new Set(entries.map((entry) => entry.source_item_id));
  return {
    changed: compared.filter((row) => row.placed || row.moved || row.resized),
    kept: compared.filter((row) => !(row.placed || row.moved || row.resized)).map((row) => row.entry),
    missing: tasks.filter((task) => task.acceptance === "accepted" && !held.has(task.id)),
  };
}
