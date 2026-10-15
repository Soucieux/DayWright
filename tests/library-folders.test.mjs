import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { folderSummary, folderTicks } from "../src/library/libraryData.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const file = (relativePath, tasks = []) => ({ id: relativePath, origin: "folder", folderId: "folder_1", relativePath,
  tasks: tasks.map((itemId) => ({ itemId, role: "reference" })) });

test("a folder's row counts its files and the tasks that use them, each task once", () => {
  const items = [file("01 Basics.md", ["item_a"]), file("02 Signals.md", ["item_a", "item_b"]), file("README.md")];

  assert.deepEqual(folderSummary(items), { files: 3, tasks: 2 });
  assert.deepEqual(folderSummary([]), { files: 0, tasks: 0 });
});

test("Change files starts from the files in the Library; a file a task uses can't be unticked", () => {
  const preview = [
    { path: "01 Basics.md", ticked: true, reason: null },
    { path: "02 Signals.md", ticked: true, reason: null },
    { path: "README.md", ticked: true, reason: null },
    { path: "history/old.md", ticked: false, reason: "skipped" },
  ];
  const inFolder = [file("01 Basics.md", ["item_a", "item_b"]), file("02 Signals.md")];

  const { unticked, used } = folderTicks(preview, inFolder);

  assert.deepEqual([...unticked], ["README.md"], "a file left out of the Library starts unticked; one never tickable isn't listed");
  assert.deepEqual(used, { "01 Basics.md": 2 });
});

test("the Library lists one row per folder; opening one shows its own view with a way back", () => {
  const screen = source("library/LibraryScreen.jsx");
  assert.match(screen, /<section className="dw-card dw-sources">\s*<ul className="dw-folder-rows">/, "under the Folders tab, which names them");
  assert.match(screen, /groups\.folders\.map\(\(\{ folder, items: inFolder \}\) => \(\s*<FolderRow key=\{folder\.id\}/);
  assert.doesNotMatch(screen, /libraryFolderGroup/, "no folder lists its files on the Library's page any more");
  assert.match(screen, /className="dw-back" onClick=\{\(\) => setOpenFolder\(null\)\}><Icon name="left" size=\{18\} \/>\{t\("navLibrary"\)\} \/ \{shown\.folder\.title\}/);
  // The folder's view holds what its card held: Refresh, Update location, its files with Open and Remove, Show all; and Change files….
  assert.match(screen, /<SourceGroup id=\{shown\.folder\.id\} icon="folder"/);
  assert.match(screen, /onChangeFiles=\{\(\) => setSheet\(\{ kind: "files", folder: shown\.folder \}\)\}/);
  const row = source("library/SourceList.jsx");
  assert.match(row, /export function FolderRow\(/);
  assert.match(row, /\{folder\.path\}/);
  assert.match(row, /t\(files === 1 \? "folderFileCountOne" : "folderFileCount", \{ count: files \}\)/);
  assert.match(row, /folder\.found \?/);
  assert.match(row, /\{t\("updateLocationAction"\)\}/);
  assert.match(row, /onClick=\{onChangeFiles\}>\s*<Icon name="check" size=\{18\} \/>\{t\("changeFilesAction"\)\}/);
});

test("Change files is centred at 720 px, with a used file ticked and locked beside its tasks", () => {
  const sheets = source("library/FolderSheets.jsx");
  assert.match(sheets, /<CentredSheet title=\{t\("changeFilesTitle", \{ title: folder\.title \}\)\} wide onClose=\{onClose\}>/);
  assert.match(sheets, /api\(`\/api\/sources\/folder\/\$\{encodeURIComponent\(folder\.id\)\}\/ticks`, \{ method: "PUT"/);
  assert.match(sheets, /checked=\{file\.ticked && !unticked\.has\(file\.path\)\} disabled=\{!file\.ticked \|\| Boolean\(used\[file\.path\]\)\}/);
  assert.match(sheets, /t\(used\[file\.path\] === 1 \? "folderFileUsedOne" : "folderFileUsed", \{ count: used\[file\.path\] \}\)/);
});

test("the Library's folder words, in English and Chinese", () => {
  const keys = ["folderFileCount", "folderFileCountOne", "folderFound", "folderMissingShort", "changeFilesAction",
    "changeFilesTitle", "changeFilesNote", "folderFileUsed", "folderFileUsedOne", "openFolderLabel"];
  for (const language of ["en", "zh"]) for (const key of keys) assert.ok(text[language][key], `${language} ${key}`);
  assert.equal(text.en.changeFilesAction, "Change files…");
  assert.equal(text.en.folderFileUsed.replace("{count}", 2), "Used by 2 tasks");
  assert.equal(text.zh.folderFileUsed.replace("{count}", 2), "有 2 个任务在用");
});
