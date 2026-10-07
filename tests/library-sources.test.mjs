import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { briefingView, findInLibrary, libraryGroups, locateChoices, openActions, sourceView, wantsBriefing } from "../src/library/libraryData.js";
import { folderTree } from "../src/library/folderTree.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const outline = (title, ...topics) => ({ title, line: 1, topics: topics.map((topic) => ({ title: topic, line: 2 })) });
const FOLDERS = [
  { id: "f1", title: "Notes", path: "/tmp/Notes", website: "https://lessons.example", domain: "learning", found: true },
  { id: "f2", title: "Old", path: "/tmp/Old", website: null, domain: "work", found: false },
];
const ITEMS = [
  { id: "w", title: "Signals atlas", origin: "website", domain: "learning", briefing: "A map of every signal.", outline: [outline("Signals", "Computed")],
    address: "https://atlas.example/" },
  { id: "n", title: "Grammar", origin: "note", sourceType: "note", domain: "learning", briefing: "Verb endings by tense.", outline: [] },
  { id: "b", title: "Basics", origin: "folder", folderId: "f1", relativePath: "Angular/01 Basics.md", domain: "learning",
    briefing: "The very start of it all.", outline: [outline("Basics", "Setup")], missing: false },
  { id: "a", title: "Consuming HTTP Services", origin: "folder", folderId: "f1", relativePath: "Angular/03 HTTP.pdf", domain: "learning",
    briefing: "How HttpClient sends requests.", outline: [outline("Consuming HTTP Services", "Interceptors")], missing: true },
  { id: "o", title: "Plan", origin: "folder", folderId: "f2", relativePath: "plan.docx", domain: "work", briefing: null, outline: [] },
  { id: "c", title: "Desk plan.md · 0123456789ab", origin: "file", sourceType: "document", domain: "work", briefing: "Where the desk goes.", outline: [] },
];

test("a folder's file is named by its heading and its kind read from its path; a website is a website", () => {
  assert.deepEqual(sourceView(ITEMS[2]), { name: "Basics", kind: "markdown", group: "folders" });
  assert.equal(sourceView(ITEMS[3]).kind, "pdf");
  assert.equal(sourceView(ITEMS[4]).kind, "word");
  assert.deepEqual(sourceView(ITEMS[0]), { name: "Signals atlas", kind: "website", group: "websites" });
  assert.deepEqual(sourceView(ITEMS[5]), { name: "Desk plan.md", kind: "markdown", group: "files" });
});

test("the Library groups by where each came from: folders with their files in path order, then websites, files and notes", () => {
  const all = libraryGroups(ITEMS, FOLDERS);
  assert.deepEqual(all.folders.map(({ folder, items }) => [folder.id, items.map((item) => item.id)]), [["f1", ["b", "a"]], ["f2", ["o"]]]);
  assert.deepEqual([all.website, all.file, all.note].map((group) => group.map((item) => item.id)), [["w"], ["c"], ["n"]]);
});

test("finding in the Library looks at names, briefings and headings", () => {
  assert.deepEqual(findInLibrary(ITEMS, "  signal ").map((item) => item.id), ["w"]);
  assert.deepEqual(findInLibrary(ITEMS, "interceptors").map((item) => item.id), ["a"]);
  assert.deepEqual(findInLibrary(ITEMS, "DESK").map((item) => item.id), ["c"]);
  assert.deepEqual(findInLibrary(ITEMS, " "), []);
});

test("a source opens in its app, on its folder's website, or in the browser; a note or imported file has nothing to open", () => {
  assert.deepEqual(openActions(ITEMS[2], FOLDERS[0]), { app: true, website: true, browser: false });
  assert.deepEqual(openActions(ITEMS[3], FOLDERS[0]), { app: false, website: true, browser: false }, "a missing file can't open in its app");
  assert.deepEqual(openActions(ITEMS[4], FOLDERS[1]), { app: false, website: false, browser: false }, "nor one in a folder not found");
  assert.deepEqual(openActions(ITEMS[0], undefined), { app: false, website: false, browser: true });
  assert.deepEqual(openActions(ITEMS[1], undefined), { app: false, website: false, browser: false });
});

test("a briefing shows what it is about and its first- and second-level headings, never the text", () => {
  assert.deepEqual(briefingView({ ...ITEMS[2], briefingBy: "source", outlineBy: "source" }),
    { text: "The very start of it all.", by: "source", headings: [{ title: "Basics", topics: ["Setup"] }], outlineBy: "source", wants: false });
  assert.equal(briefingView(ITEMS[4]).text, null);
  assert.equal(wantsBriefing(ITEMS[4]), true, "no briefing");
  assert.equal(wantsBriefing(ITEMS[1]), true, "a note without headings");
  assert.equal(wantsBriefing({ ...ITEMS[0], outline: [] }), false, "a website keeps only its own headings");
  assert.equal(wantsBriefing({ ...ITEMS[0], briefing: "A map." }), true, "a briefing too short to go on");
});

test("Locate offers the folder's files, a copy Refresh added among them, but not one linked to a goal or the file's old place", () => {
  const preview = { files: [{ path: "Angular/01 Basics.md", ticked: true, reason: null }, { path: "Angular/03 HTTP v2.pdf", ticked: true, reason: null },
    { path: "Angular/03 HTTP.pdf", ticked: true, reason: null }, { path: "history/old.md", ticked: false, reason: "skipped" },
    { path: "huge.pdf", ticked: false, reason: "too large" }] };
  const inFolder = [...ITEMS.filter((item) => item.folderId === "f1").map((item) => (item.id === "b" ? { ...item, goalId: "goal_1" } : item)),
    { id: "copy", origin: "folder", folderId: "f1", relativePath: "Angular/03 HTTP v2.pdf", goalId: null, missing: false }];
  assert.deepEqual(locateChoices(preview, inFolder, ITEMS[3]), ["Angular/03 HTTP v2.pdf", "history/old.md"]);
});

test("a folder's tree lists each folder's files under it, with their tick boxes and reasons", () => {
  const files = [{ path: "README.md", ticked: true, reason: null }, { path: "Angular/01 Basics.md", ticked: true, reason: null },
    { path: "Angular/deep/x.md", ticked: true, reason: null }, { path: "history/old.md", ticked: false, reason: "skipped" }];
  assert.deepEqual(folderTree(files).map(({ folder, files: listed }) => [folder, listed.map((file) => file.name)]),
    [["", ["README.md"]], ["Angular", ["01 Basics.md"]], ["Angular/deep", ["x.md"]], ["history", ["old.md"]]]);
});

test("a file imported from the Mac's own window opens where it is, says when its original is gone, and is located again", () => {
  const imported = { ...ITEMS[5], originalPath: "/tmp/Desk plan.md", originalFound: true };
  assert.deepEqual(openActions(imported, undefined), { app: true, website: false, browser: false });
  assert.deepEqual(openActions({ ...imported, originalFound: false }, undefined), { app: false, website: false, browser: false });
  const list = source("library/SourceList.jsx");
  assert.match(list, /t\("originalNotFound"\)/);
  assert.match(list, /\/original`/);
  assert.match(list, /\/api\/sources\/files\/choose/);
  const add = source("library/LibrarySheets.jsx");
  assert.match(add, /\/api\/sources\/files\/choose/, "Choose files… asks the Mac's own window");
  assert.match(add, /\/api\/sources\/files\/import/);
  assert.match(add, /\/api\/knowledge\/import/, "the browser's own upload stays, text only");
});

test("every new Library text exists in both languages, and the Library still never calls its items sources", () => {
  for (const key of ["libraryFolderGroup", "libraryWebsiteGroup", "libraryFileGroup", "libraryNoteGroup", "connectFolderAction",
    "addWebsiteAction", "openWithAction", "folderNotFound", "updateLocationAction", "fileNotFound", "locateAction",
    "removeFromLibraryAction", "refreshAction", "briefingSuggestedByAva", "openAction", "openOnWebsiteAction", "opensInBrowser",
    "lookingIntoSite", "fromSourceAction", "originalNotFound", "locateOriginalAction", "locateOriginalLabel"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
  assert.equal(text.en.libraryOfflineLine,
    "Everything stays on this Mac; DayWright only looks a website up when you create a learning task from it, and again when that task starts.");
  assert.equal(text.en.fromSourceAction, "From a source");
});

test("Learning's Subjects ask Ava from the area page", () => {
  assert.match(source("records/AreaScreen.jsx"), /<SubjectsCard key="subjects" [^>]*onAskAva=\{onAskAva\}/);
});

test("no folder or path is assumed anywhere in the interface", () => {
  for (const path of ["library/LibraryScreen.jsx", "library/LibrarySheets.jsx", "library/FolderSheets.jsx", "library/SourceBriefing.jsx",
    "records/FromSourceSheet.jsx", "i18n.jsx"]) {
    assert.doesNotMatch(source(path), /\/Users\/|~\/Documents|\/Volumes\/|Knowledge Transfer|Professional Quality|observatory/i, path);
  }
});
