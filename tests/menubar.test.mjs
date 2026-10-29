import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import { RENEW_MENU_BAR } from "../src/api.js";
import { source } from "./interfaceText.mjs";

/** The Mac app's menu bar source. */
const shell = () => source("../src-tauri/src/menubar.rs");
/** The Mac app's main source. */
const main = () => source("../src-tauri/src/main.rs");

test("one native menu, built from the service's model at one address, replaces the panel", () => {
  assert.match(shell(), /const MENU_PATH: &str = "\/api\/now\/menu";/);
  assert.match(source("../backend/app/main.py"), /MENU_PATH = "\/api\/now\/menu"/);
  for (const gone of ["menubar/MenuBarPanel.jsx", "menubar/panel.js"]) assert.equal(existsSync(new URL(`../src/${gone}`, import.meta.url)), false, gone);
  assert.doesNotMatch(source("App.jsx"), /isPanelView|MenuBarPanel/);
  assert.doesNotMatch(source("../backend/app/desktop.py"), /PANEL_VIEW/);
  assert.doesNotMatch(shell(), /WebviewWindowBuilder|PANEL/, "no panel window");
  assert.doesNotMatch(source("bench.css"), /\.dw-menubar/);
});

test("a left click opens the menu, attached and ready before any click; a right click opens nothing", () => {
  assert.match(shell(), /\.show_menu_on_left_click\(true\)/);
  assert.match(shell(), /set_show_menu_on_right_click\(false\)/);
  // Whichever view gets the click, a right click on the status item is held back before AppKit can show the menu.
  assert.match(shell(), /addLocalMonitorForEventsMatchingMask_handler\(\s*NSEventMask::RightMouseDown \| NSEventMask::RightMouseUp,/);
  assert.match(shell(), /tray\.set_menu\(Some\(menu\)\)/);
  assert.doesNotMatch(shell(), /TrayIconEvent::Click/, "no click handler of its own: the menu is the status item's");
});

test("its items keep apart from the app menu's, as Tauri hands a tray's menu events to every listener", () => {
  assert.match(shell(), /const MENU_ID_PREFIX: &str = "menubar:";/);
  assert.match(main(), /const SETTINGS_ITEM: &str = "settings";/);
});

test("the window asks the shell to renew the title and menu after any change, which the shell answers", () => {
  assert.equal(RENEW_MENU_BAR, "daywright://refresh");
  const api = source("api.js");
  assert.match(api, /options\.method && options\.method !== "GET" && window\.daywrightShell === "desktop"/);
  assert.match(main(), /url\.scheme\(\) == menubar::SHELL_SCHEME/);
  assert.match(main(), /menubar::renew\(&handle\)/);
  assert.match(shell(), /pub const SHELL_SCHEME: &str = "daywright";/);
});

test("the workbench tells the service its language, for the menu bar, and reloads when its window returns", () => {
  assert.match(source("App.jsx"), /api\("\/api\/interface-language", \{ method: "PUT", body: JSON\.stringify\(\{ language \}\) \}\)/);
  assert.match(source("workspace.js"), /addEventListener\("visibilitychange", reload\)/);
});
