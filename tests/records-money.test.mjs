import assert from "node:assert/strict";
import test from "node:test";
import { enteredCents, money } from "../src/records/money.js";

test("reads entered amounts as exact cents", () => {
  assert.equal(enteredCents("12.5"), 1250);
  assert.equal(enteredCents(" 0.07 "), 7);
  assert.equal(enteredCents("120"), 12000);
});

test("accepts a negative amount only where it is allowed", () => {
  assert.equal(enteredCents("-40.25", true), -4025);
  assert.throws(() => enteredCents("-40.25"));
});

test("refuses amounts it can't read exactly", () => {
  for (const value of ["12.345", "1,200", "abc", "", "9999999999999999"]) {
    assert.throws(() => enteredCents(value), undefined, value);
  }
});

test("shows cents with two decimals and grouped thousands", () => {
  assert.equal(money(272150), "2,721.50");
  assert.equal(money(7), "0.07");
  assert.equal(money(-1200), "−12.00");
});
