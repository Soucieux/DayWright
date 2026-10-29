import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { dayAndMonth } from "../time";
import { Icon } from "../ui/Icon";
import { EntryFields } from "./EntryFields";
import { MEMORY_AREAS, RULE_KINDS, areaName, daysText, entryLine, missingFields, ruleWhat } from "./memory";

/** The two sets of how you work, from your records, as the service words them: all time, then the last 30 days. */
const RECORD_SETS = [["allTime", "memoryRecordsAllTime"], ["lastThirty", "memoryRecordsLastThirty"]];

/**
 * One entry's row: its tag, what it holds and when it was said, with Edit and Delete as icon buttons at its end. Edit
 * opens its fields under it, saved through the service's checks; Delete asks once more and then deletes it for good.
 * @param {object} props
 * @param {object} props.entry - The entry.
 * @param {React.ReactNode} props.tag - Its tag: a rule's kind or a note's area.
 * @param {string} props.title - What it holds.
 * @param {string} props.caption - Its end and the day it was said.
 * @param {boolean} props.busy - Whether a change is being saved.
 * @param {(entry: object) => Promise<boolean>} props.onSave - Save the entry as edited; whether it saved.
 * @param {(entry: object) => Promise<boolean>} props.onDelete - Delete it for good; whether it was deleted.
 * @param {boolean} [props.editable=true] - Whether it can be edited, as a past entry can't.
 */
function EntryRow({ entry, tag, title, caption, busy, onSave, onDelete, editable = true }) {
  const { t, language } = useI18n();
  const [step, setStep] = useState("view");
  const [draft, setDraft] = useState(entry);
  const line = entryLine(entry, t, language);
  const incomplete = draft.kind === "rule" ? missingFields(draft).length > 0 : !draft.wording?.trim();
  return (
    <li className="dw-set-row">
      {tag}
      <span className="dw-set-row-main">
        <span className="dw-set-title">{title}</span>
        <span className="dw-set-caption">{caption}</span>
      </span>
      {step === "view" && (
        <span className="dw-set-row-end">
          {editable && (
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("memoryEditNamed", { line })}
              onClick={() => { setDraft(entry); setStep("edit"); }}><Icon name="pencil" size={18} /></button>
          )}
          <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("memoryDeleteNamed", { line })}
            onClick={() => setStep("delete")}><Icon name="trash" size={18} /></button>
        </span>
      )}
      {step === "edit" && (
        <form className="dw-memory-edit dw-set-row-note" onSubmit={async (event) => {
          event.preventDefault();
          if (await onSave(draft)) setStep("view");
        }}>
          <EntryFields entry={draft} onChange={setDraft} withEnd />
          <div className="dw-actions">
            <button type="submit" className="dw-button dw-button-primary" disabled={busy || incomplete}>{t("memorySave")}</button>
            <button type="button" className="dw-button dw-button-quiet" onClick={() => { setDraft(entry); setStep("view"); }}>{t("cancel")}</button>
          </div>
        </form>
      )}
      {step === "delete" && (
        <div className="dw-confirm-remove dw-set-row-note" role="alertdialog" aria-label={t("memoryDeleteQuestion")}>
          <p className="dw-step">{t("stepTwoOfTwo")}</p>
          <p><strong>{t("memoryDeleteQuestion")}</strong> {line}</p>
          <p className="dw-caption">{t("memoryDeleteNote")}</p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-danger" disabled={busy} onClick={() => onDelete(entry)}>
              <Icon name="trash" size={18} />{t("memoryDeleteAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setStep("view")}>{t("cancel")}</button>
          </div>
        </div>
      )}
    </li>
  );
}

/**
 * Settings › Memory: what Ava remembers. Rules, each tagged with its kind, what and on which days, until when and the
 * day said; notes, each tagged with its area, their words, the day said and until when; how the user works, from
 * their records (see backend/app/how_you_work.py), which can't be edited as it changes with them; and, folded under
 * Past, the entries whose end has passed, which Ava no longer reads. A rule or note can be edited, and any entry
 * deleted for good in two steps. None of it needs the model.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {() => void} props.onChanged - Read the day again, as a rule changed changes today's plans.
 */
export function MemorySection({ backendConnected, onChanged }) {
  const { t, language } = useI18n();
  const [memory, setMemory] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pastOpen, setPastOpen] = useState(false);

  /** Load what Ava remembers; a failure stays on show. */
  const load = useCallback(async () => {
    try {
      setMemory(await api("/api/memory"));
    } catch (caught) {
      setError(caught.message);
    }
  }, []);

  useEffect(() => {
    if (backendConnected) load();
  }, [backendConnected, load]);

  /** Save or delete an entry, then show what is kept and read the day again; whether it was done. */
  async function change(request) {
    setBusy(true);
    setError("");
    try {
      setMemory(await request());
      onChanged();
      return true;
    } catch (caught) {
      setError(caught.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  /** Keep an entry as edited. */
  const save = (entry) => change(() => api(`/api/memory/${encodeURIComponent(entry.id)}`, { method: "PUT", body: JSON.stringify(entry) }));
  /** Forget an entry. */
  const remove = (entry) => change(() => api(`/api/memory/${encodeURIComponent(entry.id)}`, { method: "DELETE" }));
  /** The day an entry was said, as day and month. */
  const said = (entry) => dayAndMonth(entry.saidOn, language);
  /** The day an entry ends, as day and month. */
  const ends = (entry) => dayAndMonth(entry.endsOn, language);
  const empty = memory && !memory.rules.length && !memory.notes.length && !memory.past.length;
  const notes = memory ? MEMORY_AREAS.flatMap((area) => memory.notes.filter((note) => note.area === area)) : [];
  /** An entry's tag: a rule's kind, or a note's area. */
  const kindTag = (entry) => <span className="dw-set-tag">{entry.kind === "rule" ? t(RULE_KINDS[entry.ruleKind]) : areaName(entry.area, t)}</span>;

  return (
    <section className="dw-settings-section">
      {!backendConnected ? <p className="dw-set-lead">{t("settingsServiceOff")}</p> : <p className="dw-set-lead">{t("memoryLead")}</p>}
      {backendConnected && memory && (
        <>
          {empty && <p className="dw-caption">{t("memoryEmpty")}</p>}
          {memory.rules.length > 0 && (
            <div className="dw-set-group">
              <div className="dw-set-head"><h3 className="dw-set-heading">{t("memoryRulesHeading")}</h3></div>
              <ul className="dw-set-list">
                {memory.rules.map((rule) => (
                  <EntryRow key={rule.id} entry={rule} busy={busy} onSave={save} onDelete={remove}
                    tag={kindTag(rule)}
                    title={`${ruleWhat(rule, t)} · ${daysText(rule.days, t, language)}`}
                    caption={`${rule.endsOn ? t("memoryUntilStart", { date: ends(rule) }) : t("memoryNoEnd")} · ${t("memorySaid", { date: said(rule) })}`} />
                ))}
              </ul>
            </div>
          )}
          {notes.length > 0 && (
            <div className="dw-set-group">
              <div className="dw-set-head"><h3 className="dw-set-heading">{t("memoryNotesHeading")}</h3></div>
              <ul className="dw-set-list">
                {notes.map((note) => (
                  <EntryRow key={note.id} entry={note} busy={busy} onSave={save} onDelete={remove}
                    tag={kindTag(note)} title={note.wording}
                    caption={`${t("memorySaidStart", { date: said(note) })} · ${note.endsOn ? t("memoryUntil", { date: ends(note) }) : t("memoryNoEndLater")}`} />
                ))}
              </ul>
            </div>
          )}
          {RECORD_SETS.some(([key]) => memory.records?.[key]?.length) && (
            <div className="dw-set-group">
              <div className="dw-set-head"><h3 className="dw-set-heading">{t("memoryRecordsHeading")}</h3></div>
              <p className="dw-set-caption">{t("memoryRecordsLead")}</p>
              <ul className="dw-set-list">
                {RECORD_SETS.filter(([key]) => memory.records[key].length).map(([key, label]) => [
                  <li key={key} className="dw-set-subhead">{t(label)}</li>,
                  ...memory.records[key].map((line, place) => <li key={`${key}-${place}`} className="dw-set-row"><span className="dw-set-row-main">
                    <span className="dw-set-line">{line}</span></span></li>),
                ])}
              </ul>
            </div>
          )}
          {memory.past.length > 0 && (
            <div className="dw-set-group">
              <button type="button" className="dw-set-disclosure" aria-expanded={pastOpen} aria-controls="dw-memory-past"
                onClick={() => setPastOpen((open) => !open)}>
                <Icon name={pastOpen ? "down" : "right"} size={16} />{t("memoryPastToggle", { count: memory.past.length })}</button>
              {pastOpen && (
                <div id="dw-memory-past" className="dw-set-group">
                  <p className="dw-set-caption">{t("memoryPastLead")}</p>
                  <ul className="dw-set-list dw-memory-past">
                    {memory.past.map((entry) => (
                      <EntryRow key={entry.id} entry={entry} busy={busy} onSave={save} onDelete={remove} editable={false}
                        tag={kindTag(entry)}
                        title={entry.kind === "rule" ? `${ruleWhat(entry, t)} · ${daysText(entry.days, t, language)}` : entry.wording}
                        caption={`${t("memorySaidStart", { date: said(entry) })} · ${t("memoryEnded", { date: ends(entry) })}`} />
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </section>
  );
}
