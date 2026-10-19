/**
 * Settings' panes and what their rows show: the toolbar's order and keys, each state's pill, the models folder's path
 * cut to fit, and the demo's state line. Nothing here reads the service; the panes pass in what it gave.
 */

/** Settings' panes in the toolbar's order, each with its name's key and its icon. */
export const PANES = [["models", "settingsModels", "chip"], ["memory", "settingsMemory", "brain"], ["schedule", "settingsSchedule", "calendar"],
  ["demo", "settingsDemo", "laptop"]];

/** The most characters of the models folder's path its row shows; the rest is cut from its middle. */
export const PATH_CHARACTERS = 48;

/** The keys that move between the panes, each from the pane at `place` of `count`, to the place it moves to. */
const PANE_KEYS = {
  ArrowRight: (place, count) => (place + 1) % count,
  ArrowLeft: (place, count) => (place - 1 + count) % count,
  Home: () => 0,
  End: (place, count) => count - 1,
};

/**
 * The pane a key moves to and chooses, as a tab list's keys do: ← and → to the one before or after, round the end;
 * Home and End to the first and the last.
 * @param {string} current - The pane on show.
 * @param {string} key - The key pressed.
 * @returns {string|null} The pane, or null for any other key.
 */
export function paneAfter(current, key) {
  const move = PANE_KEYS[key];
  if (!move) return null;
  return PANES[move(PANES.findIndex(([id]) => id === current), PANES.length)][0];
}

/** Each model state's pill: its tone, icon and words. */
const MODEL_PILLS = {
  ready: { tone: "success", icon: "check", label: "pillReady" },
  checking: { tone: "neutral", icon: "clock", label: "pillChecking" },
  mismatch: { tone: "danger", icon: "x", label: "pillMismatch" },
};
const MISSING_PILL = { tone: "warning", icon: "alert", label: "pillMissing" };

/**
 * A model's state as its row's pill: Ready, Checking…, Doesn't match, or Missing for one not in the folder or with no
 * folder to look in.
 * @param {string} state - The model's state, as the service gives it.
 * @returns {{tone: string, icon: string, label: string}} The pill's tone, icon and its words' key.
 */
export function modelPill(state) {
  return MODEL_PILLS[state] || MISSING_PILL;
}

/**
 * The runner's state as its row's pill: Found or Not found.
 * @param {string} state - `found` or `notFound`.
 * @returns {{tone: string, icon: string, label: string}} The pill's tone, icon and its words' key.
 */
export function runnerPill(state) {
  return state === "found" ? { tone: "success", icon: "check", label: "pillFound" } : { tone: "warning", icon: "alert", label: "pillNotFound" };
}

/**
 * A path cut in its middle to `most` characters, so its start and the folder's own name stay in view.
 * @param {string} path - The path.
 * @param {number} [most=PATH_CHARACTERS] - The most characters to show.
 * @returns {string} The path, or its start and end with "…" between them.
 */
export function middleCut(path, most = PATH_CHARACTERS) {
  if (path.length <= most) return path;
  const end = Math.floor((most - 1) / 2);
  return `${path.slice(0, most - 1 - end)}…${path.slice(path.length - end)}`;
}

/**
 * The demo's state line: open now, made on a day and kept until reset, or not made yet.
 * @param {boolean} demoMode - Whether the demo is open.
 * @param {string|null} madeOn - The day the demo was made, YYYY-MM-DD, or null when it isn't there.
 * @returns {{key: string, values: object}} The line's key and its values.
 */
export function demoState(demoMode, madeOn) {
  if (demoMode) return { key: "demoStateOpen", values: {} };
  return madeOn ? { key: "demoStateMade", values: { date: madeOn } } : { key: "demoStateNotMade", values: {} };
}
