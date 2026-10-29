import assert from "node:assert/strict";
import test from "node:test";
import { cardWords } from "../src/guide/guideCards.js";
import { taskTimeCell } from "../src/records/taskList.js";
import { WORD_LIMIT } from "../src/wording.js";
import { guideCard, interfaceText, source } from "./interfaceText.mjs";

const text = interfaceText();
const TODAY = "2026-10-14";

test("a timed task's time reads start–end in bold, its length under it", () => {
  assert.deepEqual(taskTimeCell({ date: TODAY, start_time: "19:00", duration_minutes: 30 }, TODAY, "en"),
    { range: "19:00–19:30", length: "30 min", took: null });
  assert.deepEqual(taskTimeCell({ date: TODAY, start_time: "09:00", duration_minutes: 90 }, TODAY, "zh"),
    { range: "09:00–10:30", length: "1 小时 30 分", took: null });
});

test("an estimated length is marked ≈, on its end and its length", () => {
  assert.deepEqual(taskTimeCell({ date: TODAY, start_time: "09:30", duration_minutes: 45, durationSource: "estimate" }, TODAY, "en"),
    { range: "09:30–≈10:15", length: "≈45 min", took: null });
});

test("an untimed task reads Untimed, with its length under it", () => {
  assert.deepEqual(taskTimeCell({ date: TODAY, start_time: null, duration_minutes: 30, durationSource: "estimate" }, TODAY, "en"),
    { range: null, length: "≈30 min", took: null });
  assert.deepEqual(taskTimeCell({ date: TODAY, start_time: null, duration_minutes: 20 }, TODAY, "en"),
    { range: null, length: "20 min", took: null });
});

test("a past task with the time it took says so; today's and a past one without it don't", () => {
  const timed = { start_time: "14:00", duration_minutes: 30, actualStart: "14:00", actualEnd: "14:42" };
  assert.equal(taskTimeCell({ ...timed, date: "2026-10-12" }, TODAY, "en").took, "42 min");
  assert.equal(taskTimeCell({ ...timed, date: "2026-10-12" }, TODAY, "zh").took, "42 分钟");
  assert.equal(taskTimeCell({ ...timed, date: TODAY }, TODAY, "en").took, null);
  assert.equal(taskTimeCell({ date: "2026-10-12", start_time: "14:00", duration_minutes: 30 }, TODAY, "en").took, null);
  assert.equal(taskTimeCell({ ...timed, date: "2026-10-12", actualEnd: "14:00" }, TODAY, "en").took, null,
    "a task skipped as it began took no time, and says nothing");
});

test("the columns are named in both languages, with No goal and took N min", () => {
  assert.deepEqual(["taskColTime", "taskColArea", "taskColTask", "taskColGoal", "taskColStatus"].map((key) => text.en[key]),
    ["Time", "Area", "Task", "Goal", "Status"]);
  assert.deepEqual(["taskColTime", "taskColArea", "taskColTask", "taskColGoal", "taskColStatus"].map((key) => text.zh[key]),
    ["时间", "领域", "任务", "目标", "状态"]);
  assert.deepEqual([text.en.taskNoGoal, text.zh.taskNoGoal], ["No goal", "无目标"]);
  assert.deepEqual([text.en.taskTook, text.zh.taskTook], ["took {length}", "用时 {length}"]);
});

test("one card holds every day in a table: column headers, then each day a group under its heading", () => {
  const list = source("records/TasksScreen.jsx");
  assert.match(list, /<section className="dw-card dw-task-list">/);
  assert.match(list, /<table className="dw-task-table" role="table" aria-label=\{t\("tasksTitle"\)\}>/);
  assert.match(list, /<thead role="rowgroup">\s*<tr role="row">/);
  assert.match(list, /<th scope="col" role="columnheader" className="dw-col-time">\{t\("taskColTime"\)\}<\/th>/);
  assert.match(list, /\{!hideArea && <th scope="col" role="columnheader" className="dw-col-area">\{t\("taskColArea"\)\}<\/th>\}/);
  for (const [column, key] of [["task", "taskColTask"], ["goal", "taskColGoal"], ["status", "taskColStatus"]]) {
    assert.match(list, new RegExp(`<th scope="col" role="columnheader" className="dw-col-${column}">\\{t\\("${key}"\\)\\}</th>`), column);
  }
  assert.match(list, /<tbody role="rowgroup" aria-labelledby=\{`dw-tasks-\$\{date\}`\}>/);
  assert.match(list, /<th id=\{`dw-tasks-\$\{date\}`\} colSpan=\{columns\} scope="rowgroup" role="rowheader" className="dw-task-day">\{fullDate\(date, language\)\}\{past && <Icon name="lock" size=\{16\} label=\{t\("cellReadOnly"\)\} \/>\}<\/th>/);
  assert.match(list, /<td role="cell" colSpan=\{columns\}><h2 className="dw-section-label dw-tasks-past">\{t\("pastDaysHeading", \{ count: PAST_DAYS \}\)\}<\/h2><\/td>/,
    "the past days keep their heading, a cell's heading since a header cell can't hold one");
});

test("each row: its time, its area as a tag, the task, its goal or No goal, and its status as now", () => {
  const list = source("records/TasksScreen.jsx");
  assert.match(list, /<span className="dw-task-range">\{cell\.range \|\| t\("untimed"\)\}<\/span>/);
  assert.match(list, /<span className="dw-caption">\{cell\.length\}<\/span>/);
  assert.match(list, /\{cell\.took && <span className="dw-caption dw-task-took">\{t\("taskTook", \{ length: cell\.took \}\)\}<\/span>\}/);
  assert.match(list, /\{!hideArea && <td role="cell" className="dw-task-area"><AreaTag domain=\{item\.domain\} \/><\/td>\}/);
  assert.match(list, /\{goal \? goal\.title : <span className="dw-task-no-goal">\{t\("taskNoGoal"\)\}<\/span>\}/);
  assert.match(list, /<StatusControl readOnly value=\{item\.completion_status\} noReply=\{noReplyOf\(item\)\} \/>/);
});

test("today's and later rows open the task, the whole row or its title's button; past rows are history", () => {
  const list = source("records/TasksScreen.jsx");
  assert.match(list, /<tr key=\{item\.id\} role="row" className=\{past \? "dw-task-row" : "dw-task-row dw-task-row-open"\} onClick=\{past \? undefined : \(\) => onOpen\(item\)\}>/);
  assert.match(list, /\{past \? <span className="dw-task-title">\{item\.title\}<\/span> : \(/);
  assert.match(list, /<button type="button" className="dw-task-open" aria-label=\{`\$\{item\.title\}, \$\{item\.start_time \|\| t\("untimed"\)\}, \$\{t\(item\.completion_status\)\}\. \$\{t\("openDetails"\)\}`\}\s*onClick=\{\(event\) => \{ event\.stopPropagation\(\); onOpen\(item\); \}\}>\{item\.title\}<\/button>/);
});

test("the Guide's Tasks card says it is one table, that rows from today on open, and its range", () => {
  const card = guideCard("tasks");
  assert.equal(card.for, "every task in one table.");
  assert.equal(card.do, "add, edit, filter by area; open rows from today on; 14 days back, 60 ahead.");
  assert.ok(cardWords(card) <= WORD_LIMIT, `${cardWords(card)} words`);
});

test("an area's Tasks tab leaves out the Area column; the Tasks screen keeps it", () => {
  assert.match(source("records/AreaScreen.jsx"), /<TaskList day=\{day\} today=\{today\} backendConnected=\{backendConnected\} area=\{domain\} hideArea onOpenTask=\{onOpenTask\} \/>/);
  assert.match(source("records/TasksScreen.jsx"), /<TaskList day=\{day\} today=\{today\} backendConnected=\{backendConnected\} area=\{area\} onOpenTask=\{onOpenTask\} \/>/);
});

test("the columns fill the card, the task's widest; cells are centred; in a narrow card each row stacks in three lines", () => {
  const css = source("bench.css");
  assert.match(css, /\.dw-task-table \{ width: 100%; table-layout: fixed; border-collapse: collapse; \}/);
  assert.match(css, /\.dw-task-table \.dw-col-time \{ width: 112px; \}/);
  assert.match(css, /\.dw-task-table \.dw-col-area \{ width: 88px; \}/);
  assert.match(css, /\.dw-task-table \.dw-col-goal \{ width: 28%; \}/);
  assert.match(css, /\.dw-task-table \.dw-col-status \{ width: 160px; text-align: right; \}/);
  assert.match(css, /\.dw-task-status \.dw-status-readonly \{ justify-content: flex-end; white-space: nowrap; \}/, "Not done · no reply on one line");
  assert.match(css, /\.dw-task-table td \{[^}]*vertical-align: middle;/);
  assert.match(css, /\.dw-task-list \{ container-type: inline-size; \}/);
  assert.match(css, /@container \(max-width: 720px\) \{\s*\.dw-task-table thead \{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect\(0 0 0 0\); \}/,
    "on a phone, or wherever the card is too narrow for its columns, the header row is hidden from sight, still read aloud");
  assert.match(css, /\.dw-task-row \{ display: grid; grid-template-columns: auto auto 1fr; grid-template-areas: "time area status" "task task task" "goal goal goal";/);
});
