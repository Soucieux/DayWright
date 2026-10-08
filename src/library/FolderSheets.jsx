import { useEffect, useId, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { SheetForm } from "../records/SheetForm";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Sheet } from "../ui/Sheet";
import { WORD_LIMIT, countWords } from "../wording";
import { folderTree } from "./folderTree";
import { locateChoices } from "./libraryData";

/** Why a file in a folder's tree starts unticked, by the reason the local service gives. */
const REASON_KEYS = { hidden: "folderReasonHidden", skipped: "folderReasonSkipped", "too large": "folderReasonTooLarge" };

/** The file types Open with sets an app for, with their names. */
const OPEN_WITH_KINDS = [["md", "kindMarkdown"], ["pdf", "kindPdf"], ["docx", "kindWord"]];

/** The longest app name Open with keeps, as the local service takes it. */
const APP_NAME_CHARACTERS = 80;

/**
 * A folder anywhere on this Mac: picked in the Mac's own window, or typed. Nothing is assumed: no
 * folder is suggested, and the field starts empty.
 * @param {object} props
 * @param {string} props.path - The folder's path so far.
 * @param {(path: string) => void} props.onPath - Type a path, or take the one picked.
 * @param {(path: string) => void} [props.onChosen] - Take a folder picked in the Mac's window.
 * @param {boolean} props.backendConnected - Whether the Mac's window can be asked for.
 */
export function FolderPicker({ path, onPath, onChosen, backendConnected }) {
  const { t } = useI18n();
  const fieldId = useId();
  const [choosing, setChoosing] = useState(false);
  const [error, setError] = useState("");

  async function choose() {
    setChoosing(true);
    setError("");
    try {
      const answer = await api("/api/sources/folder/choose", { method: "POST" });
      if (answer.path) {
        onPath(answer.path);
        onChosen?.(answer.path);
      }
    } catch (caught) {
      setError(caught.message);
    } finally {
      setChoosing(false);
    }
  }

  return (
    <div className="dw-field dw-folder-picker">
      <button type="button" className="dw-button" disabled={!backendConnected || choosing} onClick={choose}>
        <Icon name="folder" size={18} />{choosing ? t("choosingFolderLabel") : t("chooseFolderAction")}</button>
      <label className="dw-field-label" htmlFor={fieldId}>{t("folderPathLabel")}</label>
      <input id={fieldId} type="text" spellCheck={false} autoComplete="off" maxLength={4096} value={path}
        onChange={(event) => onPath(event.target.value)} />
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </div>
  );
}

/**
 * A folder's readable files as a tree of tick boxes, each folder in it able to tick or untick all its
 * files at once. A file left out at first, being hidden, in a folder such as history, or too large to
 * read, stays unticked with its reason.
 * @param {object} props
 * @param {{path: string, ticked: boolean, reason: string|null}[]} props.files - The folder's files, as its preview lists them.
 * @param {Set<string>} props.unticked - The files the user unticked.
 * @param {(unticked: Set<string>) => void} props.onChange - Tick or untick files.
 */
export function FolderTreeChoice({ files, unticked, onChange }) {
  const { t } = useI18n();
  const tickable = files.filter((file) => file.ticked);
  const kept = tickable.filter((file) => !unticked.has(file.path)).length;

  /**
   * Tick or untick every file a folder in the tree holds, its subfolders' too.
   * @param {string} folder - The folder's path in the tree.
   * @param {boolean} tick - Tick them, or untick them.
   */
  function setFolder(folder, tick) {
    const next = new Set(unticked);
    for (const file of tickable.filter((entry) => entry.path.startsWith(`${folder}/`))) {
      if (tick) next.delete(file.path); else next.add(file.path);
    }
    onChange(next);
  }

  function setFile(path, tick) {
    const next = new Set(unticked);
    if (tick) next.delete(path); else next.add(path);
    onChange(next);
  }

  if (!files.length) return <p className="dw-muted">{t("folderNoFiles")}</p>;
  return (
    <fieldset className="dw-folder-tree">
      <legend className="dw-field-label">{t("folderTreeHeading", { count: kept, total: files.length })}</legend>
      {folderTree(files).map(({ folder, files: inFolder }) => {
        const inside = tickable.filter((file) => file.path.startsWith(`${folder}/`));
        const all = inside.length > 0 && inside.every((file) => !unticked.has(file.path));
        const some = inside.some((file) => !unticked.has(file.path));
        return (
          <div key={folder || "."} className="dw-folder-tree-group" style={{ "--dw-depth": folder ? folder.split("/").length - 1 : 0 }}>
            {folder ? (
              <label className="dw-check dw-folder-tree-folder">
                <input type="checkbox" checked={all} disabled={!inside.length}
                  ref={(node) => { if (node) node.indeterminate = some && !all; }}
                  onChange={(event) => setFolder(folder, event.target.checked)} />
                <Icon name="folder" size={16} /><span>{folder}</span>
              </label>
            ) : <p className="dw-caption dw-folder-tree-folder">{t("folderRoot")}</p>}
            <ul>
              {inFolder.map((file) => (
                <li key={file.path}>
                  <label className="dw-check">
                    <input type="checkbox" checked={file.ticked && !unticked.has(file.path)} disabled={!file.ticked}
                      onChange={(event) => setFile(file.path, event.target.checked)} />
                    <Icon name="file" size={16} /><span>{file.name}</span>
                    {file.reason && <span className="dw-caption">{t(REASON_KEYS[file.reason])}</span>}
                  </label>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </fieldset>
  );
}

/**
 * Connect a folder: pick or type it, read its tree, untick what to leave out, and give, if you like,
 * the website its files are also on. The folder itself is only read.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be read or saved.
 * @param {(folder: object) => Promise<void>} props.onConnected - Take the folder once it is connected.
 * @param {() => void} [props.onCancel] - Leave without connecting, when there's somewhere to go back to.
 */
export function FolderConnector({ backendConnected, onConnected, onCancel }) {
  const { t } = useI18n();
  const [path, setPath] = useState("");
  const [preview, setPreview] = useState(null);
  const [unticked, setUnticked] = useState(new Set());
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  /**
   * Read the folder's tree, before anything is kept.
   * @param {string} chosen - The folder's path.
   */
  async function read(chosen) {
    if (!chosen.trim()) { setError(t("folderPathNeeded")); return; }
    setBusy("read");
    setError("");
    try {
      setPreview(await api("/api/sources/folder/preview", { method: "POST", body: JSON.stringify({ path: chosen.trim() }) }));
      setUnticked(new Set());
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy("");
    }
  }

  async function connect() {
    setBusy("connect");
    setError("");
    try {
      const folder = await api("/api/sources/folder", { method: "POST", body: JSON.stringify({
        path: preview.path, unticked: [...unticked], website: website.trim() }) });
      await onConnected(folder);
    } catch (caught) {
      setError(caught.message);
      setBusy("");
    }
  }

  return (
    <div className="dw-form dw-folder-connector">
      <p className="dw-caption">{t("folderReadOnlyNote")}</p>
      <FolderPicker path={path} backendConnected={backendConnected} onChosen={read}
        onPath={(typed) => { setPath(typed); setPreview(null); }} />
      {!preview && (
        <button type="button" className="dw-button" disabled={!backendConnected || busy === "read"} onClick={() => read(path)}>
          <Icon name="search" size={18} />{t("readFolderAction")}</button>
      )}
      {preview && (
        <>
          <FolderTreeChoice files={preview.files} unticked={unticked} onChange={setUnticked} />
          <label className="dw-field">{t("folderWebsiteLabel")}
            <input type="url" inputMode="url" spellCheck={false} placeholder="https://" maxLength={2000} value={website}
              onChange={(event) => setWebsite(event.target.value)} />
            <span className="dw-caption">{t("folderWebsiteNote")}</span></label>
        </>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-actions">
        {preview && (
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || Boolean(busy)} onClick={connect}>
            <Icon name="check" size={18} />{busy === "connect" ? t("connectingLabel") : t("connectAction")}</button>
        )}
        {onCancel && <button type="button" className="dw-button dw-button-quiet" onClick={onCancel}>{t("cancel")}</button>}
      </div>
    </div>
  );
}

/**
 * The Library's sheet to connect a folder.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be read or saved.
 * @param {(folder: object) => Promise<void>} props.onConnected - Refresh once the folder is connected.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function ConnectFolderSheet({ backendConnected, onConnected, onClose }) {
  const { t } = useI18n();
  return (
    <Sheet title={t("connectFolderTitle")} onClose={onClose}>
      <FolderConnector backendConnected={backendConnected} onCancel={onClose}
        onConnected={async (folder) => { await onConnected(folder); onClose(); }} />
    </Sheet>
  );
}

/**
 * Give a folder that moved, was renamed or unplugged its place again. Nothing in the Library is
 * removed meanwhile; once found, it is read again.
 * @param {object} props
 * @param {{id: string, title: string, path: string}} props.folder - The folder not found.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(refreshed: object) => Promise<void>} props.onSaved - Refresh once it is found again.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function UpdateLocationSheet({ folder, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [path, setPath] = useState("");

  async function submit() {
    if (!path.trim()) throw new Error(t("folderPathNeeded"));
    const refreshed = await api(`/api/sources/folder/${encodeURIComponent(folder.id)}/relocate`, {
      method: "POST", body: JSON.stringify({ path: path.trim() }) });
    await onSaved(refreshed);
  }

  return (
    <SheetForm title={t("updateLocationTitle", { title: folder.title })} submitLabel={t("updateLocationAction")}
      note={t("updateLocationNote")} backendConnected={backendConnected} onSubmit={submit} onClose={onClose}>
      <p className="dw-caption">{t("folderNotFound", { path: folder.path })}</p>
      <FolderPicker path={path} onPath={setPath} backendConnected={backendConnected} />
    </SheetForm>
  );
}

/**
 * Find a file not found in its folder: the folder's files not already in the Library are listed to
 * pick the one it is now, but not one a task uses, as the local service keeps it. Its tasks, checklists and
 * briefing stay with it.
 * @param {object} props
 * @param {object} props.source - The file not found.
 * @param {string} props.name - Its name as listed.
 * @param {{id: string, title: string, path: string}} props.folder - Its folder.
 * @param {object[]} props.inFolder - The folder's files in the Library.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => Promise<void>} props.onSaved - Refresh once it is located.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function LocateSheet({ source, name, folder, inFolder, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [choices, setChoices] = useState(null);
  const [chosen, setChosen] = useState("");
  const [error, setError] = useState("");
  // The folder is read again only when it, or the files from it that tasks use, change.
  const used = inFolder.filter((item) => item.tasks?.length).map((item) => item.relativePath).join("\n");

  useEffect(() => {
    let live = true;
    const kept = used.split("\n").filter(Boolean).map((relativePath) => ({ relativePath, tasks: [relativePath] }));
    api("/api/sources/folder/preview", { method: "POST", body: JSON.stringify({ path: folder.path }) })
      .then((preview) => { if (live) setChoices(locateChoices(preview, kept, source)); })
      .catch((caught) => { if (live) setError(caught.message); });
    return () => { live = false; };
  }, [folder.path, used, source]);

  async function submit() {
    if (!chosen) throw new Error(t("locateNone"));
    await api(`/api/sources/${encodeURIComponent(source.id)}/locate`, { method: "POST", body: JSON.stringify({ relativePath: chosen }) });
    await onSaved();
  }

  return (
    <SheetForm title={t("locateTitle", { name })} submitLabel={t("locateAction")} note={t("locateNote", { folder: folder.title })}
      backendConnected={backendConnected && Boolean(choices?.length)} onSubmit={submit} onClose={onClose}>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      {choices === null && !error && <p className="dw-caption" role="status">{t("loadingLibrary")}</p>}
      {choices && !choices.length && <p className="dw-muted">{t("locateNone")}</p>}
      {choices?.length > 0 && (
        <fieldset className="dw-choice-list">
          <legend className="dw-visually-hidden">{t("locateTitle", { name })}</legend>
          {choices.map((path) => (
            <label key={path} className="dw-check">
              <input type="radio" name="dw-locate" value={path} checked={chosen === path} onChange={() => setChosen(path)} />
              <Icon name="file" size={16} /><span>{path}</span>
            </label>
          ))}
        </fieldset>
      )}
    </SheetForm>
  );
}

/**
 * Save a website to the Library by its address, with what it is about if you like, in at most the word
 * limit. Nothing is looked up now; it is looked up when a learning task is made from it, and again as that
 * task starts.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(site: object) => Promise<void>} props.onSaved - Refresh once it is saved.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function AddWebsiteSheet({ backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [address, setAddress] = useState("");
  const [briefing, setBriefing] = useState("");
  const countId = useId();

  async function submit() {
    const site = await api("/api/sources/website", { method: "POST",
      body: JSON.stringify({ address: address.trim(), briefing: briefing.trim() }) });
    await onSaved(site);
  }

  return (
    <SheetForm title={t("addWebsiteTitle")} submitLabel={t("addWebsiteAction")} note={t("websiteSavedNote")}
      backendConnected={backendConnected} onSubmit={submit} onClose={onClose}>
      <label className="dw-field">{t("websiteAddressLabel")}
        <input type="url" inputMode="url" required spellCheck={false} placeholder="https://" maxLength={2000} pattern="https?://.+"
          value={address} onInvalid={(event) => event.target.setCustomValidity(t("websiteNeedsAddress"))}
          onChange={(event) => { event.target.setCustomValidity(""); setAddress(event.target.value); }} /></label>
      <label className="dw-field">{t("websiteBriefingLabel")}
        <textarea rows={3} maxLength={600} value={briefing} aria-describedby={countId}
          onChange={(event) => {
            // The form waits, saying why, while what it's about runs past the word limit.
            event.target.setCustomValidity(countWords(event.target.value) > WORD_LIMIT ? t("briefingTooLong", { limit: WORD_LIMIT }) : "");
            setBriefing(event.target.value);
          }} />
        <span id={countId} className={`dw-caption${countWords(briefing) > WORD_LIMIT ? " dw-word-over" : ""}`}>
          {t("wordCountLine", { count: countWords(briefing), limit: WORD_LIMIT })}</span></label>
    </SheetForm>
  );
}

/**
 * Open with: the app each kind of file from a connected folder opens in, one row per kind. Markdown
 * offers Obsidian when it's installed; any kind may name another app.
 * @param {object} props
 * @param {Record<string, string>} props.openWith - The apps chosen so far, by kind.
 * @param {boolean} props.obsidian - Whether Obsidian is installed.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => Promise<void>} props.onSaved - Refresh once it is saved.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function OpenWithSheet({ openWith, obsidian, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const first = (kind) => openWith[kind] || (kind === "md" && obsidian ? "obsidian" : "default");
  const [chosen, setChosen] = useState(Object.fromEntries(OPEN_WITH_KINDS.map(([kind]) => [kind, first(kind)])));
  const choice = (kind) => (["default", "obsidian"].includes(chosen[kind]) ? chosen[kind] : "other");

  async function submit() {
    const named = Object.fromEntries(Object.entries(chosen).map(([kind, app]) => [kind, app.trim() || "default"]));
    await api("/api/sources/open-with", { method: "PUT", body: JSON.stringify(named) });
    await onSaved();
  }

  return (
    <SheetForm title={t("openWithTitle")} submitLabel={t("saveAction")} note={t("openWithNote")} backendConnected={backendConnected}
      onSubmit={submit} onClose={onClose}>
      {OPEN_WITH_KINDS.map(([kind, key]) => (
        <div key={kind} className="dw-field dw-open-with-row">
          <span className="dw-field-label">{t(key)}</span>
          <MenuSelect label={t(key)} value={choice(kind)}
            onChange={(value) => setChosen({ ...chosen, [kind]: value === "other" ? "" : value })}
            options={[{ value: "default", label: t("openWithDefault") },
              ...(kind === "md" && obsidian ? [{ value: "obsidian", label: t("openWithObsidian") }] : []),
              { value: "other", label: t("openWithOther") }]} />
          {choice(kind) === "other" && (
            <label className="dw-field">{t("openWithAppName", { kind: t(key) })}
              <input type="text" required maxLength={APP_NAME_CHARACTERS} value={chosen[kind]}
                onChange={(event) => setChosen({ ...chosen, [kind]: event.target.value })} /></label>
          )}
        </div>
      ))}
    </SheetForm>
  );
}
