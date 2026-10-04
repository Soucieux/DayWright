import assert from "node:assert/strict";
import test from "node:test";
import { sectionLabel } from "../src/calendar/sectionLabel.js";
import { monthTitle } from "../src/calendar/month.js";
import { fullDate, shortDate } from "../src/time.js";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

test("a part of a wider Summary report is named as a day, a week or a month", () => {
  assert.equal(sectionLabel({ periodKind: "day", periodKey: "2026-10-03", start: "2026-10-03", end: "2026-10-03" }, t, "en"),
    fullDate("2026-10-03", "en"));
  assert.equal(sectionLabel({ periodKind: "week", periodKey: "2026-W40", start: "2026-09-28", end: "2026-09-30" }, t, "zh"),
    `reportWeekLabel ${JSON.stringify({ week: 40, from: shortDate("2026-09-28", "zh"), to: shortDate("2026-09-30", "zh") })}`);
  assert.equal(sectionLabel({ periodKind: "month", periodKey: "2026-09", start: "2026-09-01", end: "2026-09-30" }, t, "en"),
    monthTitle("2026-09", "en"));
});
