import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { EntryFields } from "./EntryFields";
import { MEMORY_AREAS, RULE_KINDS, areaName, daysText, entryLine, missingFields, ruleWhat, shortDay } from "./memory";

// The two sets of how you work, from your records, as the service words them: all time, then the last 30 days.
const RECORD_SETS = [["allTime", "memoryRecordsAllTime"], ["lastThirty", "memoryRecordsLastThirty"]];

/**
 * One entry's Edit and Delete: Edit opens its fields in place, saved through the service's checks; Delete asks
 * once more and then deletes it for good.
 * @param {object} props
 * @param {object} props.entry - The entry.
 * @param {boolean} props.busy - Whether a change is being saved.
 * @param {(entry: object) => Promise<boolean>} props.onSave - Save the entry as edited; whether it saved.
 * @param {(entry: object) => Promise<boolean>} props.onDelete - Delete it for good; whether it was deleted.
 * @param {boolean} [props.editable=true] - Whether it can be edited, as a past entry can't.
 */
function EntryActions({ entry, busy, onSave, onDelete, editable = true }) {
  const { t, language } = useI18n();
  const [step, setStep] = useState("view");
  const [draft, setDraft] = useState(entry);
  const line = entryLine(entry, t, language);
  const incomplete = draft.kind === "rule" ? missingFields(draft).length > 0 : !draft.wording?.trim();
  if (step === "edit") {
    return (
      <form className="dw-memory-edit" onSubmit={async (event) => {
        event.preventDefault();
        if (await onSave(draft)) setStep("view");
      }}>
        <EntryFields entry={draft} onChange={setDraft} withEnd />
        <div className="dw-actions">
          <button type="submit" className="dw-button dw-button-primary" disabled={busy || incomplete}>{t("memorySave")}</button>
          <button type="button" className="dw-button dw-button-quiet" onClick={() => { setDraft(entry); setStep("view"); }}>{t("cancel")}</button>
        </div>
      </form>
    );
  }
  if (step === "delete") {
    return (
      <div className="dw-confirm-remove" role="alertdialog" aria-label={t("memoryDeleteQuestion")}>
        <p className="dw-step">{t("stepTwoOfTwo")}</p>
        <p><strong>{t("memoryDeleteQuestion")}</strong> {line}</p>
        <p className="dw-caption">{t("memoryDeleteNote")}</p>
        <div className="dw-actions">
          <button type="button" className="dw-button dw-button-danger" disabled={busy} onClick={() => onDelete(entry)}>
            <Icon name="trash" size={18} />{t("memoryDeleteAction")}</button>
          <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setStep("view")}>{t("cancel")}</button>
        </div>
      </div>
    );
  }
  return (
    <span className="dw-memory-actions">
      {editable && (
        <button type="button" className="dw-button dw-button-quiet" aria-label={t("memoryEditNamed", { line })}
          onClick={() => { setDraft(entry); setStep("edit"); }}><Icon name="pencil" size={16} />{t("editAction")}</button>
      )}
      <button type="button" className="dw-button dw-button-quiet" aria-label={t("memoryDeleteNamed", { line })}
        onClick={() => setStep("delete")}><Icon name="trash" size={16} />{t("memoryDeleteEllipsis")}</button>
    </span>
  );
}

/**
 * Settings › Memory, below Models: what Ava remembers. Rules as a table of kind, what, days, end and the day said;
 * notes grouped by their area tag, each its words, the day said and its end; how the user works, from their records
 * (see backend/app/how_you_work.py), all time and the last 30 days, which can't be edited as it changes with them;
 * and Past, the entries whose end has passed, which Ava no longer reads. A rule or note can be edited, and each
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

  const save = (entry) => change(() => api(`/api/memory/${encodeURIComponent(entry.id)}`, { method: "PUT", body: JSON.stringify(entry) }));
  const remove = (entry) => change(() => api(`/api/memory/${encodeURIComponent(entry.id)}`, { method: "DELETE" }));
  const said = (entry) => shortDay(entry.saidOn, language);
  const ends = (entry) => (entry.endsOn ? shortDay(entry.endsOn, language) : t("memoryNoEnd"));
  const empty = memory && !memory.rules.length && !memory.notes.length && !memory.past.length;

  return (
    <section className="dw-settings-section" aria-labelledby="dw-settings-memory">
      <h3 id="dw-settings-memory" className="dw-section-label">{t("settingsMemory")}</h3>
      <p className="dw-muted">{t("memoryLead")}</p>
      {!backendConnected ? <p className="dw-muted">{t("settingsServiceOff")}</p> : memory && (
        <>
          {empty && <p className="dw-caption">{t("memoryEmpty")}</p>}
          {memory.rules.length > 0 && (
            <div className="dw-memory-group">
              <h4 className="dw-eyebrow">{t("memoryRulesHeading")}</h4>
              <table className="dw-memory-rules">
                <thead>
                  <tr><th scope="col">{t("memoryColumnKind")}</th><th scope="col">{t("memoryColumnWhat")}</th>
                    <th scope="col">{t("memoryColumnDays")}</th><th scope="col">{t("memoryColumnEnds")}</th>
                    <th scope="col">{t("memoryColumnFrom")}</th><th scope="col"><span className="dw-visually-hidden">{t("memoryColumnActions")}</span></th></tr>
                </thead>
                <tbody>
                  {memory.rules.map((rule) => (
                    <tr key={rule.id}>
                      <td data-label={t("memoryColumnKind")}>{t(RULE_KINDS[rule.ruleKind])}</td>
                      <td data-label={t("memoryColumnWhat")}>{ruleWhat(rule, t)}</td>
                      <td data-label={t("memoryColumnDays")}>{daysText(rule.days, t, language)}</td>
                      <td data-label={t("memoryColumnEnds")}>{ends(rule)}</td>
                      <td data-label={t("memoryColumnFrom")}>{said(rule)}</td>
                      <td><EntryActions entry={rule} busy={busy} onSave={save} onDelete={remove} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {memory.notes.length > 0 && (
            <div className="dw-memory-group">
              <h4 className="dw-eyebrow">{t("memoryNotesHeading")}</h4>
              {MEMORY_AREAS.filter((area) => memory.notes.some((note) => note.area === area)).map((area) => (
                <div key={area} className="dw-memory-area">
                  <h5 className="dw-memory-area-name">{areaName(area, t)}</h5>
                  <ul className="dw-memory-notes">
                    {memory.notes.filter((note) => note.area === area).map((note) => (
                      <li key={note.id}>
                        <span className="dw-memory-words">{note.wording}</span>
                        <span className="dw-caption">{t("memorySaid", { date: said(note) })} · {note.endsOn
                          ? t("memoryUntil", { date: ends(note) }) : t("memoryNoEnd")}</span>
                        <EntryActions entry={note} busy={busy} onSave={save} onDelete={remove} />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
          {RECORD_SETS.some(([key]) => memory.records?.[key]?.length) && (
            <div className="dw-memory-group">
              <h4 className="dw-eyebrow">{t("memoryRecordsHeading")}</h4>
              <p className="dw-caption">{t("memoryRecordsLead")}</p>
              {RECORD_SETS.filter(([key]) => memory.records[key].length).map(([key, label]) => (
                <div key={key} className="dw-memory-area">
                  <h5 className="dw-memory-area-name">{t(label)}</h5>
                  <ul className="dw-memory-notes">
                    {memory.records[key].map((line, place) => <li key={place}><span className="dw-memory-words">{line}</span></li>)}
                  </ul>
                </div>
              ))}
            </div>
          )}
          {memory.past.length > 0 && (
            <div className="dw-memory-group">
              <h4 className="dw-eyebrow">{t("memoryPastHeading")}</h4>
              <p className="dw-caption">{t("memoryPastLead")}</p>
              <ul className="dw-memory-notes dw-memory-past">
                {memory.past.map((entry) => (
                  <li key={entry.id}>
                    <span className="dw-memory-words">{entryLine({ ...entry, endsOn: null }, t, language)}</span>
                    <span className="dw-caption">{t("memorySaid", { date: said(entry) })} · {t("memoryEnded", { date: ends(entry) })}</span>
                    <EntryActions entry={entry} busy={busy} onSave={save} onDelete={remove} editable={false} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </section>
  );
}
