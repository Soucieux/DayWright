import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { SETTINGS_EVENT, avaOn, isReady, modelStateText, needsLine, needsReason, runnerText } from "../src/settings/models.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const say = (language) => (key, values = {}) => {
  assert.ok(text[language][key], `${language} ${key}`);
  return text[language][key].replace(/\{(\w+)\}/g, (match, name) => String(values[name] ?? match));
};
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

const RUNNER = "/opt/homebrew/bin/llama-server";
/** The models states the service gives, every model in `state`, the folder at `folder`. */
function states(state, folder = "/Users/me/AI-Models", runner = "found") {
  const at = (location) => (folder ? `${folder}/${location}` : null);
  return {
    folder, state: folder === null ? "none" : state === "folderNotFound" ? "notFound" : "found",
    models: [
      { role: "chat", name: "Qwen3-4B-Q4_K_M.gguf", location: at("gguf/Qwen3-4B-Q4_K_M.gguf"), state },
      { role: "embedding", name: "Qwen3-Embedding-0.6B-Q8_0.gguf", location: at("gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"), state },
      { role: "speech", name: "faster-whisper-small", location: at("whisper/faster-whisper-small"), state },
    ],
    runner: { location: RUNNER, state: runner },
  };
}

test("with no models folder chosen, Ava is off and says so, pointing to Settings", () => {
  assert.equal(avaOn(true, { state: "unavailable" }), false);
  assert.equal(avaOn(true, { state: "available" }), true);
  assert.equal(avaOn(true, { state: "ready" }), true);
  assert.equal(avaOn(false, { state: "ready" }), false, "without the local service, nothing answers");
  const none = states("noFolder", null);
  assert.equal(needsReason(none, "chat"), "chooseFolder");
  assert.equal(needsLine("avaNeedsModel", none, "chat", en, "en"), "Ava needs a local model. Choose your models folder in Settings.");
  assert.equal(needsLine("avaNeedsModel", none, "chat", zh, "zh"), "艾娃需要本地模型。请在设置中选择你的模型文件夹。");
  assert.equal(needsLine("searchNeedsModel", none, "embedding", en, "en"), "Library search needs a local model. Choose your models folder in Settings.");
  assert.equal(needsLine("voiceNeedsModel", none, "speech", en, "en"), "Voice needs a local model. Choose your models folder in Settings.");
});

test("each feature names why its model isn't ready: the folder, the model or its runner", () => {
  const gone = states("folderNotFound");
  assert.equal(needsReason(gone, "chat"), "folderNotFound");
  assert.equal(needsLine("avaNeedsModel", gone, "chat", en, "en"),
    "Ava needs a local model. The models folder isn't found at /Users/me/AI-Models; see Settings.");
  for (const state of ["missing", "mismatch", "checking"]) {
    assert.equal(needsReason(states(state), "chat"), "notReady", state);
  }
  assert.equal(needsLine("avaNeedsModel", states("missing"), "chat", en, "en"),
    "Ava needs a local model. Qwen3-4B-Q4_K_M.gguf isn't ready; Settings says why.");
  assert.equal(needsLine("avaNeedsModel", states("mismatch"), "chat", zh, "zh"), "艾娃需要本地模型。Qwen3-4B-Q4_K_M.gguf 尚未就绪，原因见设置。");
  // A missing runner leaves Ava and Library search unavailable, never voice, which doesn't use it.
  const noRunner = states("ready", "/Users/me/AI-Models", "notFound");
  assert.equal(needsReason(noRunner, "chat"), "runner");
  assert.equal(needsReason(noRunner, "embedding"), "runner");
  assert.equal(needsReason(noRunner, "speech"), null);
  assert.equal([isReady(noRunner, "chat"), isReady(noRunner, "speech")].join(), "false,true");
  assert.equal(needsLine("searchNeedsModel", noRunner, "embedding", en, "en"),
    "Library search needs a local model. Its runner, llama-server, isn't found; Settings says where DayWright looked.");
  assert.equal(needsReason(states("ready"), "chat"), null);
});

test("Settings names each model's state and the exact place it looked in", () => {
  const folder = "/Users/me/AI-Models";
  const line = (state, root = folder) => modelStateText(states(state, root).models[0], states(state, root), en);
  assert.equal(line("ready"), "Ready");
  assert.equal(line("checking"), "Checking…");
  assert.equal(line("missing"), `Missing from the folder: looked for ${folder}/gguf/Qwen3-4B-Q4_K_M.gguf`);
  assert.equal(line("mismatch"), `Doesn't match: the file at ${folder}/gguf/Qwen3-4B-Q4_K_M.gguf isn't the expected release`);
  assert.equal(line("noFolder", null), "No models folder chosen");
  assert.equal(line("folderNotFound"), `Folder not found at ${folder}`);
  assert.equal(modelStateText(states("missing").models[0], states("missing"), zh),
    `文件夹中没有：查找位置 ${folder}/gguf/Qwen3-4B-Q4_K_M.gguf`);
  // The runner is shown, not chosen: found or not, at the place DayWright looks.
  assert.equal(runnerText(states("ready").runner, en), `Found at ${RUNNER}`);
  assert.equal(runnerText(states("ready", folder, "notFound").runner, en), `Not found at ${RUNNER}`);
  assert.equal(runnerText(states("ready", folder, "notFound").runner, zh), `在 ${RUNNER} 找不到`);
  for (const key of ["settingsTitle", "settingsModels", "modelsLead", "modelsFolderLabel", "modelsNoFolder", "modelsNoFolderBody",
    "modelsFolderNotFoundBody", "modelsChooseFolder", "modelsChooseAnother", "modelsStopUsing", "modelsStopNote", "modelsUseTyped",
    "modelForChat", "modelForEmbedding", "modelForSpeech", "runnerLabel", "runnerFor", "runnerNote", "runnerMissingNote",
    "checkAgainAction", "openSettings", "settingsAction", "suggestionsNeedModel", "plansNeedModel"]) {
    en(key);
    zh(key);
  }
  assert.deepEqual([en("modelsStopUsing"), zh("modelsStopUsing")], ["Stop using this folder", "停止使用此文件夹"]);
  assert.match(en("modelsLead"), /nothing in it is written, moved or deleted/);
});

test("Settings opens from the app menu's Settings… (⌘,), the gear and every Open Settings", () => {
  assert.equal(SETTINGS_EVENT, "daywright:settings");
  const app = source("App.jsx");
  assert.match(app, /window\.addEventListener\(SETTINGS_EVENT, openSettingsSheet\)/);
  assert.match(app, /event\.key === ","/);
  assert.match(app, /<SettingsSheet /);
  assert.match(app, /<ModelsContext\.Provider value=/);
  const shell = source("shell/Shell.jsx");
  assert.equal((shell.match(/<SettingsLink \/>/g) || []).length, 2, "beside the Guide, wide and on a phone");
  assert.match(shell, /aria-label=\{t\("settingsAction"\)\}/);
  const menu = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
  assert.match(menu, /"Settings…"/);
  assert.match(menu, /CmdOrCtrl\+,/);
  assert.match(menu, /daywright:settings/);
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /api\("\/api\/models\/folder\/choose", \{ method: "POST" \}\)/);
  assert.match(sheet, /api\("\/api\/models\/folder", \{ method: "DELETE" \}\)/);
  assert.match(sheet, /runnerText\(/);
});

test("with Ava off, her panel says so alone, and nothing else sends the user to her", () => {
  const panel = source("talk/TalkPanel.jsx");
  // Only while the local service answers: without it, the honest offline view stays as it was.
  assert.match(panel, /\{backendConnected && !ava \? \(\s*<div className="dw-talk-body dw-talk-off" hidden=\{guideShown\}>\s*<NeedsModel feature="avaNeedsModel" role="chat" \/>\s*<\/div>/);
  assert.match(source("settings/NeedsModel.jsx"), /return connected && !ava \? <NeedsModel feature="avaNeedsModel" role="chat" \/> : children;/);
  assert.match(source("App.jsx"), /<ModelsContext\.Provider value=\{\{ models: day\.models, ava, connected: backendConnected \}\}>/);
  assert.match(panel, /if \(!words \|\| sending \|\| !ava\) return;/, "nothing is sent to Ava while she can't answer");
  assert.match(panel, /if \(open && ava && day\.unreadNotices\) onSeen\(\);/, "her messages stay unread until she can show them");
  assert.match(source("shell/Shell.jsx"), /unread=\{unread && ava\}/);
  // Each control that asks Ava for a card says she needs a model and offers Open Settings instead.
  for (const [path, count] of [["today/TodayScreen.jsx", 1], ["patterns/PatternsPanel.jsx", 1], ["records/Checklist.jsx", 2],
    ["records/AreaCards.jsx", 2], ["library/LibrarySearch.jsx", 1], ["plans/PlansScreen.jsx", 1]]) {
    assert.equal((source(path).match(/<AvaOnly>/g) || []).length, count, path);
  }
  // Another plan has its own route: the day's plans.
  assert.match(source("App.jsx"), /const askOtherPlan = \(\) => \(backendConnected && !ava \? openPlans\(\) : openConversation\("avaAskOtherPlan"\)\);/);
});

test("Library search, its suggestions, voice, plans and Today's card each say what they need and open Settings", () => {
  assert.match(source("library/LibrarySearch.jsx"), /<NeedsModel feature="searchNeedsModel" role="embedding" \/>/);
  assert.match(source("records/Checklist.jsx"), /<NeedsModel feature="suggestionsNeedModel" role="embedding" \/>/);
  assert.match(source("talk/TalkPanel.jsx"), /<NeedsModel feature="voiceNeedsModel" role="speech" \/>/);
  assert.match(source("plans/PlansScreen.jsx"), /<NeedsModel feature="plansNeedModel" role="chat" \/>/);
  const card = source("today/ModelCard.jsx");
  assert.match(card, /onClick=\{openSettings\}/);
  assert.doesNotMatch(card, /tryAgainAction/);
  assert.doesNotMatch(en("modelUnavailableBody"), /rules/, "Ava no longer answers by rules");
  // The folder check's line that the study check needs the local model points to Settings too.
  assert.match(source("talk/ProposalCard.jsx"),
    /view\.kind === "folderCheck" && !view\.modelChecked && \([\s\S]{0,160}onClick=\{openSettings\}>\{t\("openSettings"\)\}/);
});
