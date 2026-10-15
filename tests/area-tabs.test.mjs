import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AREA_TABS, areaTabOf, withAreaTab } from "../src/records/areaOverview.js";
import { AHEAD_DAYS, PAST_DAYS, taskDays } from "../src/records/taskList.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("an area page has two tabs, Overview then Tasks, named in both languages", () => {
  assert.deepEqual(AREA_TABS, [["overview", "areaTabOverview"], ["tasks", "areaTabTasks"]]);
  assert.deepEqual([text.en.areaTabOverview, text.en.areaTabTasks], ["Overview", "Tasks"]);
  assert.deepEqual([text.zh.areaTabOverview, text.zh.areaTabTasks], ["概览", "任务"]);
});

test("the tabs sit under the header and purpose line, controlling one panel that holds the banners on both", () => {
  const screen = source("records/AreaScreen.jsx");
  const at = (pattern) => screen.indexOf(pattern);
  assert.match(screen, /<TabList label=\{t\(domain\)\} idBase="dw-area" tabs=\{AREA_TABS\.map\(\(\[id, key\]\) => \[id, t\(key\)\]\)\} selected=\{tab\} onSelect=\{onTab\} \/>/);
  assert.match(screen, /<div id="dw-area-panel" role="tabpanel" aria-labelledby=\{`dw-area-tab-\$\{tab\}`\} className="dw-area-panel">/);
  // On a wide window the heading and the tabs stay put and the panel's body scrolls, as a page's own body does.
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.match(css, /\.dw-area-panel \{ flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; \}/);
  assert.match(css, /\.dw-area-panel > \* \{ flex-shrink: 0; \}/);
  assert.match(css, /\.dw-page:not\(:has\(> \.dw-page-body, > \.dw-area-panel > \.dw-page-body\)\)/);
  assert.ok(at("<ActionMenu") < at('className="dw-area-purpose"'), "+ Add sits in the header, over both tabs");
  assert.ok(at('className="dw-area-purpose"') < at("<TabList"));
  assert.ok(at("<TabList") < at('role="tabpanel"'));
  assert.ok(at('role="tabpanel"') < at("<PageBanners") && at("<PageBanners") < at('tab === "tasks"'), "the banners show on both tabs");
  assert.ok(at("{!isToday && (") < at('tab === "tasks"'), "so does the banner of a day other than today");
});

test("Overview is the page of cards as it was; Tasks is the Tasks screen's own list, its area fixed and no area switch", () => {
  const screen = source("records/AreaScreen.jsx");
  assert.match(screen, /\{tab === "tasks" \? \(\s*<TaskList day=\{day\} today=\{today\} backendConnected=\{backendConnected\} area=\{domain\} hideArea onOpenTask=\{onOpenTask\} \/>\s*\) : \(/);
  assert.match(screen, /<AreaColumns>/);
  assert.doesNotMatch(screen, /Segmented|TASK_FILTERS/, "no area switch shows");
  assert.match(screen, /import \{ TaskList \} from "\.\/TasksScreen"/);
  const tasks = source("records/TasksScreen.jsx");
  assert.match(tasks, /<Segmented label=\{t\("fieldArea"\)\} value=\{area\} onChange=\{setArea\}/, "the Tasks screen keeps its switch");
  assert.match(tasks, /<TaskList day=\{day\} today=\{today\} backendConnected=\{backendConnected\} area=\{area\} onOpenTask=\{onOpenTask\} \/>/);
  assert.match(tasks, /const \{ shown, upcoming, past \} = taskDays\(items \|\| \[\], area, today\)/);
  assert.match(tasks, /t\("pastDaysHeading", \{ count: PAST_DAYS \}\)/);
});

test("the list holds exactly the area's tasks: the days from today on, then the past days newest first, suggestions left out", () => {
  assert.deepEqual([PAST_DAYS, AHEAD_DAYS], [14, 60]);
  const items = [
    { id: "old", domain: "learning", date: "2026-10-10", acceptance: "accepted" },
    { id: "older", domain: "work", date: "2026-10-11", acceptance: "accepted" },
    { id: "recent", domain: "learning", date: "2026-10-12", acceptance: "accepted" },
    { id: "now", domain: "learning", date: "2026-10-14", acceptance: "accepted" },
    { id: "meeting", domain: "work", date: "2026-10-14", acceptance: "accepted" },
    { id: "offered", domain: "learning", date: "2026-10-15", acceptance: "pending" },
    { id: "later", domain: "learning", date: "2026-10-20", acceptance: "accepted" },
  ];
  const learn = taskDays(items, "learning", "2026-10-14");
  assert.deepEqual(learn.shown.map((item) => item.id), ["old", "recent", "now", "later"]);
  assert.deepEqual(learn.upcoming, ["2026-10-14", "2026-10-20"]);
  assert.deepEqual(learn.past, ["2026-10-12", "2026-10-10"]);
  assert.deepEqual(taskDays(items, "work", "2026-10-14").shown.map((item) => item.id), ["older", "meeting"]);
  assert.deepEqual(taskDays(items, "all", "2026-10-14").shown.map((item) => item.id), ["old", "older", "recent", "now", "meeting", "later"]);
});

test("a row in Tasks shows its status and opens its task, where its status is reported", () => {
  const tasks = source("records/TasksScreen.jsx");
  assert.match(tasks, /<StatusControl readOnly value=\{item\.completion_status\} noReply=\{noReplyOf\(item\)\} \/>/);
  assert.match(tasks, /onClick=\{past \? undefined : \(\) => onOpen\(item\)\}/);
  assert.match(tasks, /<TaskDay key=\{date\} date=\{date\} items=\{shown\.filter\(\(item\) => item\.date === date\)\} past=\{isPast\} today=\{today\} goals=\{goals\}\s*columns=\{columns\} hideArea=\{hideArea\} onOpen=\{onOpenTask\} \/>/);
});

test("See all <area> tasks switches the page to its Tasks tab, on every card that offers it", () => {
  const screen = source("records/AreaScreen.jsx");
  assert.match(screen, /const seeAll = \(\) => onTab\("tasks"\)/);
  assert.equal((screen.match(/onSeeAll=\{seeAll\}/g) || []).length, 4, "Today, Subjects, Carry-overs and Recently done");
  assert.doesNotMatch(screen, /onSeeAll=\{onSeeAll\}|props\.onSeeAll/);
  assert.doesNotMatch(source("App.jsx"), /onSeeAll=/, "it no longer leaves the page");
});

test("each area remembers its tab while the app runs, Overview until another is chosen", () => {
  assert.equal(areaTabOf({}, "learning"), "overview");
  const chosen = withAreaTab({}, "learning", "tasks");
  assert.equal(areaTabOf(chosen, "learning"), "tasks");
  assert.equal(areaTabOf(chosen, "work"), "overview");
  assert.equal(areaTabOf(withAreaTab(chosen, "learning", "overview"), "learning"), "overview");
  const before = {};
  withAreaTab(before, "work", "tasks");
  assert.deepEqual(before, {}, "a choice makes a new record and leaves the old one");
  const app = source("App.jsx");
  assert.match(app, /const \[areaTabs, setAreaTabs\] = useState\(\{\}\)/);
  assert.match(app, /tab=\{areaTabOf\(areaTabs, activeTab\)\} onTab=\{\(tab\) => setAreaTabs\(\(tabs\) => withAreaTab\(tabs, activeTab, tab\)\)\}/);
});
