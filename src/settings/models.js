/**
 * What the interface says about the models DayWright reads from the folder chosen in Settings: whether Ava is on,
 * why a feature's model isn't ready, and each model's and the runner's state in words. The local service gives
 * the states (`/api/models`, and `models` with each day); nothing here reads a file.
 */

/** The window event that opens Settings: the app menu's Settings… (⌘,), the gear and every Open Settings send it. */
export const SETTINGS_EVENT = "daywright:settings";

/** Open Settings from anywhere in the interface. */
export function openSettings() {
  window.dispatchEvent(new Event(SETTINGS_EVENT));
}

/** The models the runner runs; voice's model runs in the service itself. */
const RUN_BY_RUNNER = new Set(["chat", "embedding"]);

/** A model state's words in Settings, by state. */
const STATE_TEXT = {
  ready: "modelReady", checking: "modelChecking", missing: "modelMissing", mismatch: "modelMismatch",
  noFolder: "modelsNoFolder", folderNotFound: "modelsFolderNotFound",
};

/** What a feature says after its first sentence, by why its model isn't ready. */
const REASON_TEXT = {
  chooseFolder: "needsChooseFolder", folderNotFound: "needsFolderNotFound", notReady: "needsModelNotReady", runner: "needsRunner",
};

/**
 * Whether Ava answers: only with the local service and her model ready to run.
 * @param {boolean} backendConnected - Whether the local service answered.
 * @param {{state?: string}|undefined} model - The chat model's status, `unavailable` while it can't run.
 * @returns {boolean} Whether Ava is on.
 */
export function avaOn(backendConnected, model) {
  return backendConnected && Boolean(model) && model.state !== "unavailable";
}

/**
 * Why the model a feature needs isn't ready, or null when it is.
 * @param {object|undefined} models - The models states the service gives.
 * @param {"chat"|"embedding"|"speech"} role - The model the feature needs.
 * @returns {"chooseFolder"|"folderNotFound"|"notReady"|"runner"|null} The reason.
 */
export function needsReason(models, role) {
  if (!models || models.state === "none") return "chooseFolder";
  if (models.state === "notFound") return "folderNotFound";
  if (models.models.find((model) => model.role === role)?.state !== "ready") return "notReady";
  if (RUN_BY_RUNNER.has(role) && models.runner?.state === "notFound") return "runner";
  return null;
}

/**
 * Whether the model a feature needs is ready to use, its runner found when it needs one.
 * @param {object|undefined} models - The models states the service gives.
 * @param {"chat"|"embedding"|"speech"} role - The model the feature needs.
 * @returns {boolean} Whether it is ready.
 */
export function isReady(models, role) {
  return needsReason(models, role) === null;
}

/**
 * A feature's line when its model isn't ready: what it needs, then why, pointing to Settings.
 * @param {string} feature - The key of the feature's first sentence, such as `avaNeedsModel`.
 * @param {object|undefined} models - The models states the service gives.
 * @param {"chat"|"embedding"|"speech"} role - The model the feature needs.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`, which joins its sentences without a space.
 * @returns {string} Such as "Ava needs a local model. Choose your models folder in Settings."
 */
export function needsLine(feature, models, role, t, language) {
  const reason = needsReason(models, role) || "notReady";
  const model = models?.models.find((entry) => entry.role === role);
  return [t(feature), t(REASON_TEXT[reason], { path: models?.folder, model: model?.name })].join(language === "zh" ? "" : " ");
}

/**
 * A model's state in Settings, naming the exact place looked in.
 * @param {{state: string, location: string|null}} model - One of the models states.
 * @param {{folder: string|null}} models - The models states, for the folder looked in.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "Missing from the folder: looked for /…/gguf/Qwen3-4B-Q4_K_M.gguf".
 */
export function modelStateText(model, models, t) {
  return t(STATE_TEXT[model.state], { path: model.state === "folderNotFound" ? models.folder : model.location });
}

/**
 * The runner's state in Settings, at the place DayWright looks for it.
 * @param {{state: string, location: string}} runner - The runner's state.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "Found at /opt/homebrew/bin/llama-server".
 */
export function runnerText(runner, t) {
  return t(runner.state === "found" ? "runnerFound" : "runnerNotFound", { path: runner.location });
}
