/** Change kinds that leave an entry as it was. */
const UNCHANGED = new Set(["same", "reported"]);

/**
 * Identify the task an entry was scheduled from; entries the planner made alone match by title.
 * @param {object} entry - A plan entry.
 * @returns {string} Its matching key.
 */
function keyOf(entry) {
  return entry.source_item_id || `title:${entry.title}`;
}

/**
 * Say how one entry of the set plan changes in the replacement.
 * @param {object} before - The set plan's entry.
 * @param {object|null} after - The replacement's matching entry, if it has one.
 * @returns {string} `reported`, `removed`, `moved`, `shorter`, `longer` or `same`.
 */
function changeOf(before, after) {
  if (!after) return "removed";
  if (before.completion_status !== "planned") return "reported";
  if (after.start_time !== before.start_time) return "moved";
  if (after.duration_minutes < before.duration_minutes) return "shorter";
  if (after.duration_minutes > before.duration_minutes) return "longer";
  return "same";
}

/**
 * Line up a set plan and a proposed replacement entry by entry, so every change can be reviewed
 * before anything is replaced. Entries match by the task they were scheduled from, in order when a
 * task appears more than once.
 * @param {object[]} current - The set plan's entries.
 * @param {object[]} next - The replacement's entries.
 * @returns {{kind: string, before: object|null, after: object|null}[]} One row per entry, in time
 *   order. `kind` is `reported`, `same`, `shorter`, `longer`, `moved`, `removed` or `added`.
 */
export function replacementRows(current, next) {
  const waiting = new Map();
  for (const entry of next) waiting.set(keyOf(entry), [...(waiting.get(keyOf(entry)) || []), entry]);
  const matched = new Set();
  const rows = current.map((before) => {
    const after = (waiting.get(keyOf(before)) || []).find((entry) => !matched.has(entry)) || null;
    if (after) matched.add(after);
    return { kind: changeOf(before, after), before, after };
  });
  const added = next.filter((entry) => !matched.has(entry)).map((after) => ({ kind: "added", before: null, after }));
  const startOf = (row) => (row.before || row.after).start_time;
  return [...rows, ...added].sort((left, right) => startOf(left).localeCompare(startOf(right)));
}

/**
 * Count the rows of a replacement by kind of change.
 * @param {{kind: string}[]} rows - Rows from `replacementRows`.
 * @returns {{changed: number, reported: number, byKind: Object<string, number>}} How many rows change,
 *   how many were already reported, and how many of each changing kind.
 */
export function changeCounts(rows) {
  const byKind = {};
  for (const row of rows) {
    if (!UNCHANGED.has(row.kind)) byKind[row.kind] = (byKind[row.kind] || 0) + 1;
  }
  return {
    changed: Object.values(byKind).reduce((total, count) => total + count, 0),
    reported: rows.filter((row) => row.kind === "reported").length,
    byKind,
  };
}
