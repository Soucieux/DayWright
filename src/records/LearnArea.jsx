import { useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { StatusControl } from "../ui/StatusControl";
import { formatMinutes } from "../time";
import { SheetForm } from "./SheetForm";

/** How hard a subject is, with the message key naming each level. */
const DIFFICULTIES = [["easy", "difficultyEasy"], ["medium", "difficultyMedium"], ["hard", "difficultyHard"]];

/** What a study session came to, as the user reports it. */
const RESULTS = ["done", "partial", "skipped"];

/** A new session's length until the user changes it, in minutes. */
const DEFAULT_SESSION_MINUTES = 30;

/**
 * Record one study session today: which subject, how long, and what came of it. Nothing is inferred
 * from the plan.
 * @param {object} props
 * @param {string} props.date - Today's YYYY-MM-DD date.
 * @param {object[]} props.subjects - Active subjects.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function SessionSheet({ date, subjects, backendConnected, mutate, onClose }) {
  const { t, demoText } = useI18n();
  const [itemId, setItemId] = useState(subjects[0]?.id || "");
  const [minutes, setMinutes] = useState(String(DEFAULT_SESSION_MINUTES));
  const [result, setResult] = useState("done");
  return (
    <SheetForm title={t("recordSessionTitle")} submitLabel={t("saveSessionAction")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/learning/sessions", "POST", { date, itemId, minutes: Number(minutes), result })}>
      <label className="dw-field">{t("fieldSubject")}
        <select required value={itemId} onChange={(event) => setItemId(event.target.value)}>
          {subjects.map((subject) => <option key={subject.id} value={subject.id}>{demoText(subject.title)}</option>)}
        </select></label>
      <label className="dw-field">{t("fieldDuration")}
        <input type="number" min={1} max={1440} required value={minutes} onChange={(event) => setMinutes(event.target.value)} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldResult")}</span>
        <Segmented label={t("fieldResult")} value={result} onChange={setResult}
          options={RESULTS.map((value) => [value, <><Icon name={`status-${value}`} size={16} />{t(value)}</>])} /></div>
    </SheetForm>
  );
}

/**
 * A new subject to study. It is a catalogue entry, not a scheduled task.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function SubjectSheet({ backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [estimate, setEstimate] = useState(String(DEFAULT_SESSION_MINUTES));
  return (
    <SheetForm title={t("newSubjectTitle")} submitLabel={t("saveSubjectAction")} note={t("subjectNote")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/learning/items", "POST", { title: title.trim(), difficulty, estimatedMinutes: Number(estimate) })}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldDifficulty")}</span>
        <Segmented label={t("fieldDifficulty")} value={difficulty} onChange={setDifficulty} options={DIFFICULTIES.map(([value, key]) => [value, t(key)])} /></div>
      <label className="dw-field">{t("fieldEstimate")}
        <input type="number" min={1} max={1440} required value={estimate} onChange={(event) => setEstimate(event.target.value)} /></label>
    </SheetForm>
  );
}

/**
 * Learn's own records: the day's study sessions and the subjects being studied, shown by tab.
 * @param {object} props
 * @param {string} props.tab - The tab on show.
 * @param {object} props.data - The Learning snapshot for the day on show.
 * @param {boolean} props.isToday - Whether sessions can be recorded.
 * @param {boolean} props.canPrepare - Whether subjects can change.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change from a form.
 * @param {(path: string, method: string, body: object) => void} props.act - Save a change from the page.
 * @param {string|null} props.sheet - The form open, if any.
 * @param {(sheet: string|null) => void} props.setSheet - Open or close a form.
 */
export function LearnArea({ tab, data, isToday, canPrepare, backendConnected, mutate, act, sheet, setSheet }) {
  const { t, language, demoText } = useI18n();
  const show = (id) => tab === "overview" || tab === id;
  const active = data.items.filter((item) => item.status === "active");
  const difficulty = (value) => t(DIFFICULTIES.find(([key]) => key === value)?.[1] || "difficultyMedium");
  const close = () => setSheet(null);
  return (
    <>
      {show("sessions") && (
        <section className="dw-card" aria-labelledby="dw-sessions-title">
          <div className="dw-card-head">
            <h2 id="dw-sessions-title" className="dw-heading">{t("sessionsTitle")}</h2>
            {isToday && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || !active.length} onClick={() => setSheet("session")}><Icon name="plus" size={18} />{t("recordSessionAction")}</button>}
          </div>
          {isToday && !active.length && <p className="dw-caption">{t("sessionNeedsSubject")}</p>}
          {data.sessions.length ? (
            <ul className="dw-day-rows">
              {data.sessions.map((session) => (
                <li key={session.id} className="dw-day-row dw-session-row">
                  <span className="dw-day-row-title">{demoText(session.itemTitle)}<span className="dw-caption">{formatMinutes(session.minutes, language)}</span></span>
                  <StatusControl readOnly value={session.result} />
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noSessions")}</p>}
        </section>
      )}
      {show("subjects") && (
        <section className="dw-card" aria-labelledby="dw-subjects-title">
          <div className="dw-card-head">
            <h2 id="dw-subjects-title" className="dw-heading">{t("subjectsTitle")}</h2>
            {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setSheet("subject")}><Icon name="plus" size={18} />{t("newSubjectAction")}</button>}
          </div>
          {data.items.length ? (
            <ul className="dw-day-rows">
              {data.items.map((item) => (
                <li key={item.id} className="dw-day-row dw-session-row">
                  <span className="dw-day-row-title">{demoText(item.title)}
                    <span className="dw-caption">{difficulty(item.difficulty)} · {formatMinutes(item.estimatedMinutes, language)}{item.status !== "active" && ` · ${t("subjectFinished")}`}</span></span>
                  {canPrepare
                    ? <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
                      onClick={() => act(`/api/learning/items/${item.id}`, "PATCH", { status: item.status === "active" ? "done" : "active" })}>{item.status === "active" ? t("markFinishedAction") : t("reopenAction")}</button>
                    : <span />}
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noSubjectsYet")}</p>}
        </section>
      )}
      {sheet === "session" && <SessionSheet date={data.date} subjects={active} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
      {sheet === "subject" && <SubjectSheet backendConnected={backendConnected} mutate={mutate} onClose={close} />}
    </>
  );
}
