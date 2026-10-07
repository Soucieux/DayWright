import { useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { SheetForm } from "../records/SheetForm";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { importHeaders } from "./libraryData";

/** The largest file the local service imports, in bytes. */
const MAX_IMPORT_BYTES = 2_000_000;

/** File types the local service can read. */
const IMPORTABLE = /\.(md|markdown|pdf|docx)$/i;

/**
 * A file's name, from where it is on this Mac.
 * @param {string} path - Its path.
 * @returns {string} Its last part.
 */
function fileName(path) {
  return path.split("/").filter(Boolean).pop() || path;
}

/**
 * Send one chosen file to the local service to be read and indexed. It never leaves this Mac.
 * @param {File} file - The chosen file.
 * @param {(key: string) => string} t - The interface text lookup, for the reasons checked here.
 * @returns {Promise<object>} The indexed file.
 * @throws {Error} With the reason the file wasn't imported.
 */
async function importFile(file, t) {
  if (!IMPORTABLE.test(file.name)) throw new Error(t("wrongFileType"));
  if (file.size > MAX_IMPORT_BYTES) throw new Error(t("fileTooLarge"));
  const response = await fetch("/api/knowledge/import", { method: "POST", headers: importHeaders(file.name), body: file });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

/**
 * Add to the Library: write a note, or import files. Nothing asks for an area or a goal: a Learn task links what it
 * studies from its own details. Files that fail to import stay chosen, with the reason, while the rest are saved.
 * @param {object} props
 * @param {"note"|"files"} props.kind - Whether it opens to write a note or to import files.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(names: string[]) => Promise<void>} props.onSaved - Refresh after notes or files were saved, naming them.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function LibraryAddSheet({ kind: firstKind, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [kind, setKind] = useState(firstKind);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  // Files chosen in the Mac's own window, by where they are, so each remembers it and opens there.
  const [paths, setPaths] = useState([]);
  const [choosing, setChoosing] = useState(false);
  const fileRef = useRef(null);
  const chosenNames = [...paths.map(fileName), ...files.map((file) => file.name)];

  /** Choose files in the Mac's own window; each one imported remembers where it is. */
  async function chooseOnMac() {
    setChoosing(true);
    try {
      const answer = await api("/api/sources/files/choose", { method: "POST", body: JSON.stringify({ multiple: true }) });
      if (answer.paths.length) setPaths(answer.paths);
    } finally {
      setChoosing(false);
    }
  }

  async function submit() {
    if (kind === "note") {
      await api("/api/knowledge/sources", { method: "POST", body: JSON.stringify({ title: title.trim(), text: text.trim(), sourceType: "note" }) });
      await onSaved([title.trim()]);
      return;
    }
    if (!files.length && !paths.length) throw new Error(t("chooseFilesFirst"));
    const saved = [];
    const failed = [];
    if (paths.length) {
      const answer = await api("/api/sources/files/import", { method: "POST", body: JSON.stringify({ paths }) });
      saved.push(...answer.saved.map((source) => fileName(source.originalPath || source.title)));
      const kept = new Set(answer.failed.map((failure) => failure.name));
      setPaths(paths.filter((path) => kept.has(fileName(path))));
      failed.push(...answer.failed.map((failure) => [{ name: failure.name }, failure.reason, true]));
    }
    for (const file of files) {
      try {
        await importFile(file, t);
        saved.push(file.name);
      } catch (caught) {
        failed.push([file, caught.message]);
      }
    }
    if (saved.length) await onSaved(saved);
    if (failed.length) {
      setFiles(failed.filter(([, , byPath]) => !byPath).map(([file]) => file));
      throw new Error(failed.map(([file, reason]) => t("importFailed", { name: file.name, reason })).join(" "));
    }
  }

  return (
    <SheetForm title={t("addToLibraryTitle")} submitLabel={kind === "note" ? t("saveNoteAction") : t("importFilesAction")}
      note={t("notePrivacy")} backendConnected={backendConnected} onSubmit={submit} onClose={onClose}>
      <Segmented label={t("addToLibraryTitle")} value={kind} onChange={setKind}
        options={[["note", <><Icon key="icon" name="note" size={18} />{t("newNoteAction")}</>], ["files", <><Icon key="icon" name="upload" size={18} />{t("importFilesAction")}</>]]} />
      {kind === "note" ? (
        <>
          <label className="dw-field">{t("fieldTitle")}
            <input required pattern=".*\S.*" maxLength={200} value={title}
              onInvalid={(event) => event.target.setCustomValidity(t("noteTitleNeeded"))}
              onChange={(event) => { event.target.setCustomValidity(""); setTitle(event.target.value); }} /></label>
          <label className="dw-field">{t("noteTextLabel")}
            <textarea required rows={8} value={text}
              onInvalid={(event) => event.target.setCustomValidity(t("noteTextNeeded"))}
              onChange={(event) => { event.target.setCustomValidity(""); setText(event.target.value); }} /></label>
        </>
      ) : (
        <div className="dw-field"><span className="dw-field-label">{t("filesLabel")}</span>
          <div className="dw-file-choice">
            <button type="button" className="dw-button" disabled={!backendConnected || choosing} onClick={chooseOnMac}>
              <Icon name="upload" size={18} />{choosing ? t("choosingFolderLabel") : t("chooseFilesAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" onClick={() => fileRef.current?.click()}>{t("uploadCopyAction")}</button>
            <input ref={fileRef} type="file" multiple accept=".md,.markdown,.pdf,.docx" hidden
              onChange={(event) => { setFiles([...(event.target.files || [])]); event.target.value = ""; }} />
            {chosenNames.length > 0 && <ul className="dw-file-list">{chosenNames.map((name) => <li key={name}><Icon name="file" size={16} />{name}</li>)}</ul>}
          </div>
          <span className="dw-caption">{t("importLimits")}</span>
        </div>
      )}
    </SheetForm>
  );
}
