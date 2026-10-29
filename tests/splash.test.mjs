import assert from "node:assert/strict";
import test from "node:test";
import { source } from "./interfaceText.mjs";

test("the start screen names the log the desktop app wrote the reason to, from its address, never a fixed path", () => {
  const splash = source("desktop/splash.js");
  assert.doesNotMatch(splash, /Library\/Logs/);
  assert.match(splash, /const LOG = "log";/);
  assert.match(splash, /new URLSearchParams\(location\.search\)\.get\(LOG\)/);
  assert.match(source("../src-tauri/src/main.rs"), /const LOG_QUERY: &str = "log";/);
});
