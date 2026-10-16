import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { deviceText } from "../src/settings/models.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);

test("each model says where it runs: on the graphics, on the processor and why, or on standby before its first use", () => {
  const devices = [{ state: "graphics", reason: null }, { state: "processor", reason: null },
    { state: "processor", reason: "didntStart" }, { state: "processor", reason: "noDevice" },
    { state: "processor", reason: "stopped" }, { state: "standby", reason: null }];
  assert.deepEqual(devices.map((device) => deviceText(device, say("en"))), ["Graphics (Metal)", "Processor",
    "Processor: the graphics didn't start", "Processor: no graphics device found", "Processor: the graphics stopped",
    "On standby"]);
  assert.deepEqual(devices.map((device) => deviceText(device, say("zh"))), ["图形处理器（Metal）", "处理器",
    "处理器：图形处理器未能启动", "处理器：未找到图形设备", "处理器：图形处理器已停止", "待命"]);
  assert.equal(deviceText(undefined, say("en")), "", "an older service that says nothing shows nothing");
});

test("Run models on reads Automatic · Processor only in both languages, with a line on what Automatic does", () => {
  assert.deepEqual(["runModelsOn", "runOnAutomatic", "runOnProcessor"].map((key) => text.en[key]),
    ["Run models on", "Automatic", "Processor only"]);
  assert.deepEqual(["runModelsOn", "runOnAutomatic", "runOnProcessor"].map((key) => text.zh[key]),
    ["模型运行于", "自动", "仅处理器"]);
  assert.match(text.en.runModelsOnNote, /graphics \(Metal\)/);
  assert.match(text.en.runModelsOnNote, /Voice runs on the processor/);
  assert.ok(text.zh.runModelsOnNote.includes("Metal") && text.zh.runModelsOnNote.includes("语音"));
});

test("Settings › Models holds the choice under the folder, and choosing sends it to the local service", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<Segmented label=\{t\("runModelsOn"\)\} value=\{models\.runOn\} onChange=\{chooseRunOn\}\s*options=\{\[\["automatic", t\("runOnAutomatic"\)\], \["processor", t\("runOnProcessor"\)\]\]\} \/>/);
  assert.match(sheet, /const chooseRunOn = \(runOn\) => runOn !== models\.runOn\s*&& change\(\(\) => api\("\/api\/models\/run-on", \{ method: "PUT", body: JSON\.stringify\(\{ runOn \}\) \}\)\);/);
  assert.ok(sheet.indexOf('t("modelsFolderLabel")') < sheet.indexOf('t("runModelsOn")')
    && sheet.indexOf('t("runModelsOn")') < sheet.indexOf('t("settingsModels")'), "between the folder and the models");
});

test("a ready model's row says where it runs, under its file name; voice's says the processor, as the service gives it", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /\{model\.state === "ready" && models\.devices\?\.\[model\.role\] && \(\s*<span className="dw-set-caption dw-set-device">\{deviceText\(models\.devices\[model\.role\], t\)\}<\/span>/);
  assert.match(sheet, /import \{ deviceText, modelStateText \} from "\.\/models";/);
});
