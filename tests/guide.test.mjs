import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { cardWords, guideRows, guideSections, seeGuide } from "../src/guide/guideCards.js";

const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const titles = (sections) => sections.flatMap((section) => section.cards.map((card) => card.title));

test("the five sections appear in order, each with its cards", () => {
  assert.deepEqual(guide.sections.map((section) => section.title),
    ["The day", "Your work", "Library", "Ava and the agents", "Rules everywhere"]);
  assert.deepEqual(guide.sections.map((section) => section.cards.map((card) => card.title)), [
    ["Today", "Plans", "Calendar"], ["Goals", "Tasks", "Areas"], ["Library"], ["Ava", "Agents"],
    ["Past days", "Meals", "Repeats", "Energy"],
  ]);
  assert.deepEqual(guideSections(guide), guide.sections, "the Guide page shows every section, in order");
  assert.match(source("guide/Guide.jsx"), /<GuideCards sections=\{guideSections\(guide\)\}/);
});

test("every card has For, Do and Rule, at most 40 words across those three lines (title and labels not counted)", () => {
  assert.deepEqual([guide.labels.for, guide.labels.do, guide.labels.rule], ["For", "Do", "Rule"]);
  for (const card of guide.sections.flatMap((section) => section.cards)) {
    for (const line of ["for", "do", "rule"]) assert.ok(card[line]?.trim(), `${card.title} has ${line}`);
    assert.ok(cardWords(card) <= 40, `${card.title}: ${cardWords(card)} words`);
  }
  assert.equal(cardWords({ for: "running today.", do: "set your energy at 09:00–22:00.", rule: "“+ Add” here" }), 9,
    "a word holds a letter or a digit, so “+ is none and 09:00–22:00 is one");
});

test("each ? opens exactly its screen's cards, under their sections in Guide order", () => {
  const expected = {
    today: ["Today", "Energy", "Meals"], plans: ["Plans"], calendar: ["Calendar", "Past days"], goals: ["Goals"],
    tasks: ["Tasks", "Repeats"], areas: ["Areas"], library: ["Library"], ava: ["Ava", "Agents"],
  };
  assert.deepEqual(Object.keys(guide.screens).sort(), Object.keys(expected).sort());
  for (const [screen, cards] of Object.entries(expected)) {
    const sections = guideSections(guide, screen);
    assert.deepEqual(titles(sections).sort(), [...cards].sort(), screen);
    assert.deepEqual(titles(sections), titles(guide.sections).filter((title) => cards.includes(title)), `${screen} keeps Guide order`);
    assert.ok(sections.every((section) => section.cards.length > 0), `${screen} shows no empty section`);
  }
});

test("each screen's header carries its own ?, beside its title", () => {
  const screens = {
    "today/TodayScreen.jsx": ["today", 1], "plans/PlansScreen.jsx": ["plans", 2], "calendar/CalendarScreen.jsx": ["calendar", 1],
    "records/GoalsScreen.jsx": ["goals", 1], "records/TasksScreen.jsx": ["tasks", 1], "records/AreaScreen.jsx": ["areas", 1],
    "library/LibraryScreen.jsx": ["library", 1],
  };
  for (const [path, [screen, count]] of Object.entries(screens)) {
    const text = source(path);
    const buttons = [...text.matchAll(/<GuideButton screen="(\w+)"/g)];
    assert.equal(buttons.length, count, `${path} has ${count} ?`);
    for (const button of buttons) {
      assert.equal(button[1], screen, path);
      const before = text.slice(0, button.index);
      assert.match(before.slice(before.lastIndexOf("</h1>")), /^<\/h1>\s*$/, `${path}: the ? comes right after the screen's title`);
    }
  }
  assert.match(source("talk/TalkPanel.jsx"), /<GuideButton screen="ava"/, "Ava's panel has its own ?");
});

test("each card shows its icon in a circle of its section's colour, For and Do as labelled lines, and one Rule callout", () => {
  const view = source("guide/Guide.jsx");
  const card = view.slice(view.indexOf("function GuideCard("), view.indexOf("\n}\n", view.indexOf("function GuideCard(")));
  assert.match(card, /<span className="dw-guide-icon"><Icon name=\{card\.icon\}/);
  assert.match(card, /guide\.labels\.for/);
  assert.match(card, /guide\.labels\.do/);
  assert.equal((card.match(/dw-guide-rule/g) || []).length, 1, "one Rule callout");
  assert.match(card, /guide\.labels\.rule/);
  assert.match(view, /className=\{`dw-guide-section dw-guide-\$\{section\.id\}`\}/, "each section heading carries its colour");
  assert.match(view, /className=\{`dw-card dw-guide-card dw-guide-\$\{section\.id\}`\}/, "each card carries its section's colour");
  for (const item of guide.sections.flatMap((section) => section.cards)) {
    assert.ok(existsSync(new URL(`../design/icons/${item.icon}.svg`, import.meta.url)), `${item.title}'s icon is in the set`);
  }
  const css = source("bench.css");
  for (const section of guide.sections) {
    const rule = css.match(new RegExp(`\\.dw-guide-${section.id} \\{([^}]*)\\}`));
    assert.ok(rule, `${section.title} has its colours`);
    assert.match(rule[1], /--dw-guide-fg: var\(--dw-[\w-]+\); --dw-guide-tint: var\(--dw-[\w-]+\);/, `${section.title} uses tokens`);
  }
  assert.doesNotMatch(css.slice(css.indexOf("/* The Guide")), /#[0-9a-f]{3,8}\b|rgb\(/i, "no hard-coded colour");
});

test("every card is the same size: each heading is its own row, each row of cards shares one height", () => {
  const sections = [{ cards: [1, 2, 3] }, { cards: [1] }];
  assert.equal(guideRows(sections, 2), "auto 1fr 1fr auto 1fr");
  assert.equal(guideRows(sections, 1), "auto 1fr 1fr 1fr auto 1fr");
});

test("a reply's closing See Guide line names its cards, which open them; any other text is left as it is", () => {
  assert.equal(guide.labels.seeGuide, "See Guide");
  const reply = "**Meals**\nFor: keeping lunch and dinner free.\n\nSee Guide: Meals, Repeats";
  assert.deepEqual(seeGuide(guide, reply), { text: "**Meals**\nFor: keeping lunch and dinner free.",
    cards: [findCard("meals"), findCard("repeats")] });
  assert.deepEqual(seeGuide(guide, "See Guide: Past days"), { text: "", cards: [findCard("past-days")] });
  for (const text of ["Plans are proposed.", "See Guide: Holidays", "See Guide: Meals\nThen more"]) {
    assert.deepEqual(seeGuide(guide, text), { text, cards: [] }, text);
  }
});

test("the Guide link sits next to EN/中文 in the top bar and the phone header", () => {
  const shell = source("shell/Shell.jsx");
  assert.equal((shell.match(/<GuideLink [^>]*\/>\s*<LanguageToggle \/>/g) || []).length, 2);
});

function findCard(id) {
  return guide.sections.flatMap((section) => section.cards).find((card) => card.id === id);
}
