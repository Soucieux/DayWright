import assert from "node:assert/strict";
import test from "node:test";
import { textRuns } from "../src/talk/richText.js";

test("bold and italic markers in a reply become emphasis instead of showing", () => {
  assert.deepEqual(textRuns("Use the **Focused** plan, *gently*."), [
    { text: "Use the " }, { text: "Focused", strong: true }, { text: " plan, " }, { text: "gently", em: true }, { text: "." }]);
});

test("a heading loses its hashes and is shown bold", () => {
  assert.deepEqual(textRuns("## Plan\nKeep it."), [{ text: "Plan", strong: true }, { text: "\nKeep it." }]);
});

test("a bold heading and bold italics lose all their marks", () => {
  assert.deepEqual(textRuns("## **Plan**"), [{ text: "Plan", strong: true }]);
  assert.deepEqual(textRuns("### Plan ###"), [{ text: "Plan", strong: true }]);
  assert.deepEqual(textRuns("It is ***both*** now"), [{ text: "It is " }, { text: "both", strong: true, em: true }, { text: " now" }]);
});

test("an asterisk that marks nothing stays as written", () => {
  assert.deepEqual(textRuns("5 * 3 and a*b"), [{ text: "5 * 3 and a*b" }]);
  assert.deepEqual(textRuns(""), []);
});
