import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { LIBRARY_TABS, libraryCounts, libraryGroups, libraryTabOf } from "../src/library/libraryData.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);

test("the Library has four tabs, Folders, Websites, Files and Notes, with no All, each named with its count", () => {
  assert.deepEqual(LIBRARY_TABS.map(([id]) => id), ["folders", "website", "file", "note"]);
  for (const [language, names] of [["en", ["Folders", "Websites", "Files", "Notes"]], ["zh", ["文件夹", "网站", "文件", "笔记"]]]) {
    assert.deepEqual(LIBRARY_TABS.map(([, key]) => text[language][key]), names, language);
  }
  assert.equal(say("en")("libraryTabText", { name: "Folders", count: 3 }), "Folders · 3");
  assert.equal(say("en")("libraryTabName", { name: "Folders", count: 3 }), "Folders, 3", "a screen reader says Folders, 3");
  assert.equal(say("zh")("libraryTabText", { name: "文件夹", count: 3 }), "文件夹 · 3");
  assert.equal(say("zh")("libraryTabName", { name: "文件夹", count: 3 }), "文件夹，3");
});

test("each tab counts its own kind, every one shown even at 0", () => {
  const folders = [{ id: "algebra", title: "Algebra" }, { id: "spanish", title: "Spanish" }];
  const items = [
    { id: "a", origin: "folder", folderId: "algebra", relativePath: "01.md" },
    { id: "b", origin: "folder", folderId: "spanish", relativePath: "verbs.md" },
    { id: "c", origin: "website" },
    { id: "d", sourceType: "document" },
    { id: "e", sourceType: "document" },
  ];
  assert.deepEqual(libraryCounts(libraryGroups(items, folders)), { folders: 2, website: 1, file: 2, note: 0 });
  assert.deepEqual(libraryCounts(libraryGroups([], [])), { folders: 0, website: 0, file: 0, note: 0 });
});

test("the Library opens on the tab last used while the app runs; the first time on the first with anything, else Folders", () => {
  assert.equal(libraryTabOf(null, { folders: 0, website: 0, file: 2, note: 1 }), "file");
  assert.equal(libraryTabOf(null, { folders: 1, website: 0, file: 2, note: 1 }), "folders");
  assert.equal(libraryTabOf(null, { folders: 0, website: 0, file: 0, note: 0 }), "folders");
  assert.equal(libraryTabOf("note", { folders: 1, website: 0, file: 2, note: 0 }), "note", "a tab chosen stays chosen though it empties");
  const app = source("App.jsx");
  assert.match(app, /const \[libraryTab, setLibraryTab\] = useState\(null\)/);
  assert.match(app, /<LibraryScreen [^>]*tab=\{libraryTab\} onTab=\{setLibraryTab\}/);
});

test("the tabs sit under the header and the search box, which searches everything whatever the tab", () => {
  const screen = source("library/LibraryScreen.jsx");
  const at = (pattern) => screen.indexOf(pattern);
  assert.match(screen, /<TabList label=\{t\("navLibrary"\)\} idBase="dw-library"/);
  assert.match(screen, /tabs=\{LIBRARY_TABS\.map\(\(\[id, key\]\) => \[id, t\("libraryTabText", \{ name: t\(key\), count: counts\[id\] \}\)\]\)\}/);
  assert.match(screen, /names=\{Object\.fromEntries\(LIBRARY_TABS\.map\(\(\[id, key\]\) => \[id, t\("libraryTabName", \{ name: t\(key\), count: counts\[id\] \}\)\]\)\)\}/);
  assert.match(screen, /selected=\{current\} onSelect=\{onTab\}/);
  assert.match(screen, /<div id="dw-library-panel" role="tabpanel" aria-labelledby=\{`dw-library-tab-\$\{current\}`\}>/);
  assert.ok(at("</header>") < at("<LibrarySearch") && at("<LibrarySearch") < at("<TabList"), "header, then search, then the tabs");
  assert.match(screen, /<LibrarySearch items=\{items \|\| \[\]\} /, "search is given every item, never a tab's");
  assert.match(screen, /const counts = groups && libraryCounts\(groups\)/, "counts come from the Library as it is on every showing, so they follow an add or a removal at once");
  assert.match(screen, /const current = libraryTabOf\(tab, counts \|\| \{\}\)/);
});

test("on a phone the four tabs sit closer, so none is cut off at the edge; and a long list never squeezes them away", () => {
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  // The tab list scrolls sideways, so the body's grid could shrink its row to nothing under a folder's long list.
  assert.match(css, /\.dw-library-body \{ display: grid; gap: var\(--dw-space-5\); align-content: start; grid-auto-rows: max-content; \}/);
  assert.match(css, /\.dw-library-body > \.dw-tabs \{ margin: 0; \}/);
  assert.match(css, /@media \(max-width: 640px\) \{\s*\.dw-library \.dw-tabs button \{ padding: 0 var\(--dw-space-2\); \}/);
});

test("a folder's view opens inside the Folders tab, with its way back", () => {
  const screen = source("library/LibraryScreen.jsx");
  assert.match(screen, /current === "folders" \? \(\s*shown \? \(/);
  assert.ok(screen.indexOf('role="tabpanel"') < screen.indexOf('className="dw-back" onClick={() => setOpenFolder(null)}'));
});

test("an empty tab says so, with its own way to add: Connect folder, Add website, Import files, New note", () => {
  assert.deepEqual(LIBRARY_TABS.map(([id, , empty, action, icon]) => [id, empty, action, icon]), [
    ["folders", "libraryFoldersEmpty", "connectFolderAction", "folder"], ["website", "libraryWebsitesEmpty", "addWebsiteAction", "globe"],
    ["file", "libraryFilesEmpty", "importFilesAction", "upload"], ["note", "libraryNotesEmpty", "newNoteAction", "note"]]);
  for (const language of ["en", "zh"]) {
    for (const [, , empty] of LIBRARY_TABS) assert.ok(text[language][empty], `${language}.${empty}`);
  }
  assert.deepEqual(LIBRARY_TABS.map(([, , empty]) => text.en[empty]),
    ["No folders connected yet.", "No websites saved yet.", "No files imported yet.", "No notes written yet."]);
  const screen = source("library/LibraryScreen.jsx");
  assert.match(screen, /folders: \(\) => setSheet\(\{ kind: "connect" \}\), website: \(\) => setSheet\(\{ kind: "website" \}\),\s*file: \(\) => onAdd\("files"\), note: \(\) => onAdd\("note"\)/);
  assert.match(screen, /<TabEmpty tab=\{current\} onAdd=\{adders\[current\]\} backendConnected=\{backendConnected\} \/>/);
  assert.match(screen, /\{allEmpty && <p className="dw-muted dw-library-intro">\{t\("libraryEmptyBody"\)\}<\/p>\}/,
    "with nothing at all, a line still says what the Library is for");
  assert.equal(text.en.libraryEmptyTitle, undefined, "the whole-Library empty card is gone");
});
