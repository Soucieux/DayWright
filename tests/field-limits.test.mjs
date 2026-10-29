import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import test from "node:test";
import {
  ADDRESS_CHARACTERS, APP_NAME_CHARACTERS, BRIEFING_CHARACTERS, DETAIL_CHARACTERS, FOLDER_PATH_CHARACTERS, TITLE_CHARACTERS,
} from "../src/fieldLimits.js";
import { MINUTES_PER_DAY } from "../src/time.js";
import { source } from "./interfaceText.mjs";

const service = source("../backend/app/main.py");

/**
 * Every interface file under a folder, with its path from src.
 * @param {string} folder - A folder under src, or "" for src itself.
 * @returns {[string, string][]} Each file's path and text.
 */
function interfaceFiles(folder) {
  return readdirSync(new URL(`../src/${folder}`, import.meta.url), { withFileTypes: true }).flatMap((entry) => {
    const path = folder ? `${folder}/${entry.name}` : entry.name;
    if (entry.isDirectory()) return interfaceFiles(path);
    return /\.jsx?$/.test(entry.name) ? [[path, source(path)]] : [];
  });
}

test("each field takes as many characters as the service does", () => {
  for (const model of ["DailyItemCreate", "GoalCreate", "KnowledgeSourceRequest"]) {
    assert.match(service, new RegExp(`class ${model}\\(BaseModel\\):[^]*?title: str = Field\\(min_length=1, max_length=${TITLE_CHARACTERS}\\)`), model);
  }
  assert.match(service, new RegExp(`task: Optional\\[str\\] = Field\\(default=None, max_length=${TITLE_CHARACTERS}\\)`), "a task a rule keeps off");
  assert.match(service, new RegExp(`class ChecklistName\\(BaseModel\\):[^]*?title: str = Field\\(max_length=${TITLE_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`detail: str = Field\\(default="", max_length=${DETAIL_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`durationMinutes: Optional\\[int\\] = Field\\(default=None, ge=1, le=${MINUTES_PER_DAY}\\)`));
  assert.match(service, new RegExp(`class FolderPath\\(BaseModel\\):[^]*?path: str = Field\\(min_length=1, max_length=${FOLDER_PATH_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`address: str = Field\\(min_length=1, max_length=${ADDRESS_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`website: str = Field\\(default="", max_length=${ADDRESS_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`briefing: str = Field\\(default="", max_length=${BRIEFING_CHARACTERS}\\)`));
  assert.match(service, new RegExp(`md: Optional\\[str\\] = Field\\(default=None, max_length=${APP_NAME_CHARACTERS}\\)`));
});

test("no field writes its limit as a bare number", () => {
  for (const [path, text] of interfaceFiles("")) {
    assert.doesNotMatch(text, /(?:maxLength|max)=\{\d/, path);
  }
});
