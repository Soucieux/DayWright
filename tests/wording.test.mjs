import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { cardWords } from "../src/guide/guideCards.js";
import { briefingView, wantsBriefing } from "../src/library/libraryData.js";
import { BRIEFING_MIN_WORDS, WORD_LIMIT, countWords, cutWords } from "../src/wording.js";

const wording = JSON.parse(readFileSync(new URL("../src/wording.json", import.meta.url), "utf8"));
const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const LONG = Array.from({ length: WORD_LIMIT + 15 }, (_, index) => `word${index}`).join(" ");

test("the one limit and counter come from the file the service reads too", () => {
  assert.deepEqual([WORD_LIMIT, BRIEFING_MIN_WORDS], [wording.wordLimit, wording.briefingMinWords]);
  assert.equal(WORD_LIMIT, 40);
  assert.match(source("../backend/app/wording.py"), /WORDING = json\.loads\(\(PROJECT_ROOT \/ "src" \/ "wording\.json"\)/);
  assert.match(source("../scripts/build-desktop-service.sh"), /--add-data "\$\(pwd\)\/src\/wording\.json:src"/);
});

test("words are counted and cut as the service counts and cuts them", () => {
  for (const [text, count] of wording.counts) assert.equal(countWords(text), count, text);
  for (const [text, limit, cut] of wording.cuts) assert.equal(cutWords(text, limit), cut, text);
  assert.equal(countWords(cutWords(LONG)), WORD_LIMIT);
});

test("every Guide card's For, Do and Rule hold the limit, counted by the shared counter", () => {
  const card = { for: "running today.", do: "set your energy at 09:00–22:00.", rule: "“+ Add” here" };
  assert.equal(cardWords(card), countWords([card.for, card.do, card.rule].join(" ")));
  for (const each of guide.sections.flatMap((section) => section.cards)) {
    assert.ok(cardWords(each) <= WORD_LIMIT, `${each.title}: ${cardWords(each)} words`);
  }
});

test("the briefing pop-over shows at most the limit, cut at a word boundary", () => {
  const view = briefingView({ id: "s", title: "T", origin: "website", briefing: LONG, briefingBy: "source", outline: [] });
  assert.equal(countWords(view.text), WORD_LIMIT);
  assert.ok(view.text.endsWith("…"));
  assert.equal(wantsBriefing({ briefing: "资料库中的笔记", outline: [{ title: "x", topics: [] }], origin: "folder" }), false,
    "Chinese is counted a character a word, as everywhere");
});

test("a briefing the user writes, or types with a website, shows its count and waits within the limit", () => {
  for (const path of ["library/SourceBriefing.jsx", "library/FolderSheets.jsx"]) {
    const text = source(path);
    assert.match(text, /t\("wordCountLine", \{ count: countWords\(/, path);
    assert.match(text, /countWords\([^)]*\) > WORD_LIMIT/, path);
  }
});
