import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { SheetForm } from "../records/SheetForm";
import { clockOfTimestamp } from "../time";
import { entriesOn } from "./libraryData";
import { NetworkEntry } from "./NetworkLog";
import { SourceList } from "./SourceList";
import { TopicLookup } from "./TopicLookup";

/** The largest file the local service imports, in bytes. */
const MAX_IMPORT_BYTES = 2_000_000;

/** File types the local service can read. */
const IMPORTABLE = /\.(md|markdown|pdf|docx)$/i;

/**
 * Send one chosen file to the local service to be read and indexed. It never leaves this Mac.
 * @param {File} file - The chosen file.
 * @param {(key: string) => string} t - The interface text lookup, for the reasons checked here.
 * @returns {Promise<object>} The indexed source.
 * @throws {Error} With the reason the file wasn't imported.
 */
async function importFile(file, t) {
  if (!IMPORTABLE.test(file.name)) throw new Error(t("wrongFileType"));
  if (file.size > MAX_IMPORT_BYTES) throw new Error(t("fileTooLarge"));
  const filename = btoa(String.fromCharCode(...new TextEncoder().encode(file.name)));
  const response = await fetch("/api/knowledge/import", {
    method: "POST", headers: { "Content-Type": "application/octet-stream", "X-DayWright-Filename": filename }, body: file,
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

/**
 * Write a note into the Library.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(note: {title: string, text: string}) => Promise<void>} props.onSave - Save the note.
 * @param {() => void} props.onClose - Close the sheet.
 */
function NoteSheet({ backendConnected, onSave, onClose }) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  async function submit() {
    if (!text.trim()) throw new Error(t("noteTextNeeded"));
    await onSave({ title: title.trim(), text: text.trim() });
  }

  return (
    <SheetForm title={t("newNoteAction")} submitLabel={t("saveNoteAction")} note={t("notePrivacy")} backendConnected={backendConnected} onSubmit={submit} onClose={onClose}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={title}
          onInvalid={(event) => event.target.setCustomValidity(t("noteTitleNeeded"))}
          onChange={(event) => { event.target.setCustomValidity(""); setTitle(event.target.value); }} /></label>
      <label className="dw-field">{t("noteTextLabel")}
        <textarea required rows={10} value={text} onChange={(event) => setText(event.target.value)} /></label>
    </SheetForm>
  );
}

/**
 * What stays on this Mac, what went online today, and what never leaves.
 * @param {object} props
 * @param {object[]} props.entries - Today's network log entries.
 * @param {() => void} props.onOpenLog - Open the whole network log.
 */
function PrivacyLedger({ entries, onOpenLog }) {
  const { t } = useI18n();
  return (
    <section className="dw-card dw-ledger" aria-labelledby="dw-ledger-title">
      <h2 id="dw-ledger-title" className="dw-title">{t("whatStaysTitle")}</h2>
      <div className="dw-ledger-part">
        <h3 className="dw-ledger-head dw-ledger-stays"><Icon name="laptop" size={18} />{t("staysOnMac")}</h3>
        <p className="dw-muted">{t("staysOnMacList")}</p>
      </div>
      <div className="dw-ledger-part">
        <h3 className={`dw-ledger-head${entries.length ? " dw-ledger-online" : ""}`}><Icon name="globe" size={18} />{t("onlineLookupsToday", { count: entries.length })}</h3>
        {entries.length ? (
          <ul className="dw-network-log dw-network-today">
            {entries.map((entry) => (
              <li key={entry.id}><strong className="dw-network-time">{clockOfTimestamp(entry.happenedAt)}</strong><NetworkEntry entry={entry} /></li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("nothingOnlineToday")}</p>}
      </div>
      <p className="dw-ledger-line"><Icon name="offline" size={18} /><span>{t("neverSentLine")}</span></p>
      <button type="button" className="dw-link" onClick={onOpenLog}><Icon name="arrow" size={18} />{t("openNetworkLog")}</button>
    </section>
  );
}

/**
 * The Library: every note and imported file, with removal; topic lookup that stays local unless the
 * user allows one online request; and an account of what stays on this Mac and what went online.
 * @param {object} props
 * @param {object} props.day - The day on show, for the page banners.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {object[]} props.networkLog - Network log entries, newest first.
 * @param {() => void} props.onAskTalk - Open Talk to ask about the Library.
 * @param {() => void} props.onOpenLog - Open the whole network log.
 * @param {() => Promise<void>} props.onChanged - Refresh what depends on the Library after a change.
 * @param {() => void} props.onNetwork - Refresh the network log.
 */
export function LibraryScreen({ day, today, backendConnected, networkLog, onAskTalk, onOpenLog, onChanged, onNetwork }) {
  const { t } = useI18n();
  const [sources, setSources] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [report, setReport] = useState(null);
  const fileRef = useRef(null);

  async function load() {
    try {
      setSources((await api("/api/knowledge")).sources);
      setLoadError("");
    } catch (caught) {
      setLoadError(caught.message);
    }
  }

  useEffect(() => {
    if (backendConnected) load();
  }, [backendConnected]);

  async function changed() {
    await load();
    await onChanged();
  }

  /**
   * Save a written note, then list it.
   * @param {{title: string, text: string}} note - The note.
   */
  async function saveNote(note) {
    await api("/api/knowledge/sources", { method: "POST", body: JSON.stringify({ ...note, sourceType: "note" }) });
    setReport({ saved: [note.title], failed: [] });
    await changed();
  }

  /**
   * Import each chosen file in turn, then say which were saved and why any weren't.
   * @param {Event} event - The file input's change.
   */
  async function importChosen(event) {
    const files = [...(event.target.files || [])];
    event.target.value = "";
    if (!files.length) return;
    setImporting(true);
    setReport(null);
    const saved = [];
    const failed = [];
    for (const file of files) {
      try {
        await importFile(file, t);
        saved.push(file.name);
      } catch (caught) {
        failed.push([file.name, caught.message]);
      }
    }
    setImporting(false);
    setReport({ saved, failed });
    if (saved.length) await changed();
  }

  /**
   * Remove a source from the Library.
   * @param {object} source - The source.
   */
  async function removeSource(source) {
    await api(`/api/knowledge/sources/${encodeURIComponent(source.id)}`, { method: "DELETE" });
    await changed();
  }

  return (
    <main className="dw-page dw-library" tabIndex={-1}>
      <header className="dw-page-head">
        <div>
          <h1 className="dw-display">{t("navLibrary")}</h1>
          <p className="dw-body-lg">{t("libraryCaption")}</p>
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button" disabled={!backendConnected} onClick={() => setNoteOpen(true)}>
            <Icon name="note" size={18} /><span className="dw-phone-hidden">{t("newNoteAction")}</span></button>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || importing} onClick={() => fileRef.current?.click()}>
            <Icon name="upload" size={18} /><span className="dw-phone-hidden">{importing ? t("importingLabel") : t("importFilesAction")}</span></button>
          <input ref={fileRef} type="file" multiple accept=".md,.markdown,.pdf,.docx" hidden onChange={importChosen} />
        </div>
      </header>
      <p className="dw-limits"><Icon name="info" size={18} /><span>{t("importLimits")}</span></p>
      <PageBanners day={day} backendConnected={backendConnected} />
      {report && (
        <div className="dw-import-report">
          {report.saved.length > 0 && <p className="dw-banner dw-banner-saved" role="status"><Icon name="check" size={18} />{t("savedToLibrary", { names: report.saved.join(t("listSeparator")) })}</p>}
          {report.failed.map(([name, reason]) => <p key={name} className="dw-alert" role="alert">{t("importFailed", { name, reason })}</p>)}
        </div>
      )}
      <div className="dw-library-grid">
        <div className="dw-library-sources">
          {sources ? <SourceList sources={sources} today={today} backendConnected={backendConnected} onRemove={removeSource} /> : (
            <section className="dw-card">
              <p className="dw-muted">{loadError ? t("libraryLoadFailed", { reason: loadError }) : backendConnected ? t("loadingLibrary") : t("libraryNeedsService")}</p>
            </section>
          )}
        </div>
        <div className="dw-library-lookup">
          <TopicLookup backendConnected={backendConnected} onAskTalk={onAskTalk} onSaved={changed} onNetwork={onNetwork} />
        </div>
        <div className="dw-library-ledger">
          <PrivacyLedger entries={entriesOn(networkLog, today)} onOpenLog={onOpenLog} />
        </div>
      </div>
      {noteOpen && <NoteSheet backendConnected={backendConnected} onSave={saveNote} onClose={() => setNoteOpen(false)} />}
    </main>
  );
}
