import { clockOf, minutesOf } from "../time.js";
import { planChanges } from "../today/planChanges.js";

/**
 * What tells one plan from another at a glance: its first task and when, when its day ends, and
 * which task lengths it changed from the ones recorded.
 * @param {object[]} entries - The plan's entries, each naming its task in `source_item_id`.
 * @param {object[]} tasks - The day's tasks as recorded.
 * @returns {{first: {title: string, start: string}|null, doneBy: string|null, resized: {title: string, from: number, to: number}[]}}
 *   `first` and `doneBy` are null when the plan holds no task.
 */
export function planGlance(entries, tasks) {
  const ordered = [...entries].sort((first, second) => minutesOf(first.start_time) - minutesOf(second.start_time));
  const { changed } = planChanges(ordered, tasks);
  const ends = ordered.map((entry) => minutesOf(entry.start_time) + entry.duration_minutes);
  return {
    first: ordered.length ? { title: ordered[0].title, start: ordered[0].start_time } : null,
    doneBy: ends.length ? clockOf(Math.max(...ends)) : null,
    resized: changed.filter((row) => row.resized)
      .map((row) => ({ title: row.entry.title, from: row.task.duration_minutes, to: row.entry.duration_minutes })),
  };
}
