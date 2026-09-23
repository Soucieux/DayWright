import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { Sheet } from "../ui/Sheet";
import { StatusControl } from "../ui/StatusControl";
import { formatMinutes, longDate, timeRange } from "../time";
import { linkableGoals, taskDraft, taskPayload } from "./taskDraft";

/** Areas a task can belong to, in the order the area control lists them. */
const TASK_AREAS = ["learning", "life", "finance", "rest"];

/**
 * The task sheet: a form for a new task, or a task's details with Edit and Remove.
 * @param {object} props
 * @param {object|null} props.row - The row whose details to show, or null to record a new task.
 * @param {string} props.date - The date a new task belongs to.
 * @param {object[]} props.goals - The user's goals.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(payload: object, itemId: string|null) => Promise<void>} props.onSave - Save a task.
 * @param {(item: object) => Promise<void>} props.onRemove - Remove a task.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function TaskSheet({ row, date, goals, backendConnected, onSave, onRemove, onStatus, onReplace, onClose }) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(!row);
  const task = row?.source || null;
  if (editing) {
    return (
      <Sheet title={task ? t("editTaskTitle") : t("newTaskTitle")} view="form" onClose={onClose}>
        <TaskForm task={task} date={date} goals={goals} backendConnected={backendConnected} onSave={onSave}
          onDone={task ? () => setEditing(false) : onClose} onCancel={task ? () => setEditing(false) : onClose} />
      </Sheet>
    );
  }
  return (
    <Sheet title={t("taskDetailTitle")} view="detail" onClose={onClose}>
      <TaskDetail row={row} task={task} goals={goals} backendConnected={backendConnected} onStatus={onStatus}
        onEdit={() => setEditing(true)} onRemove={onRemove} onReplace={onReplace} onClose={onClose} />
    </Sheet>
  );
}

/**
 * Record or edit one task. It belongs to the day on show; nothing here schedules it into a plan.
 * @param {object} props
 * @param {object|null} props.task - The stored task, or null for a new one.
 * @param {string} props.date - The date a new task belongs to.
 * @param {object[]} props.goals - The user's goals.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(payload: object, itemId: string|null) => Promise<void>} props.onSave - Save the task.
 * @param {() => void} props.onDone - Called after a successful save.
 * @param {() => void} props.onCancel - Leave without saving.
 */
function TaskForm({ task, date, goals, backendConnected, onSave, onDone, onCancel }) {
  const { t, language, demoText } = useI18n();
  const [draft, setDraft] = useState(() => taskDraft(task, date));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const set = (fields) => setDraft((current) => ({ ...current, ...fields }));
  const goalsHere = linkableGoals(goals, draft.domain);
  const canSave = backendConnected && !saving;

  async function submit(event) {
    event.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError("");
    try {
      await onSave(taskPayload(draft), task?.id || null);
      onDone();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="dw-form" onSubmit={submit}>
      <p className="dw-caption">{t("taskForDate")} {longDate(draft.date, language).dayMonth}</p>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={draft.title}
          onInvalid={(event) => event.target.setCustomValidity(t("titleNeeded"))}
          onChange={(event) => { event.target.setCustomValidity(""); set({ title: event.target.value }); }} /></label>
      <label className="dw-field"><span>{t("fieldDetail")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <textarea maxLength={1000} rows={2} value={draft.detail} onChange={(event) => set({ detail: event.target.value })} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
        <Segmented label={t("fieldArea")} value={draft.domain} onChange={(domain) => set({ domain, goalId: "" })}
          options={TASK_AREAS.map((domain) => [domain, <AreaTag key={domain} domain={domain} plain />])} /></div>
      <div className="dw-field-row">
        <label className="dw-field">{t("fieldStart")}
          <input type="time" required value={draft.startTime} onChange={(event) => set({ startTime: event.target.value })} /></label>
        <label className="dw-field">{t("fieldDuration")}
          <input type="number" min={1} max={1440} required value={draft.durationMinutes} onChange={(event) => set({ durationMinutes: event.target.value })} /></label>
      </div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldTiming")}</span>
        <Segmented label={t("fieldTiming")} value={draft.constraintKind} onChange={(constraintKind) => set({ constraintKind })}
          options={[["flexible", t("timingFlexible")], ["fixed", t("flagFixed")]]} />
        <span className="dw-caption">{draft.constraintKind === "fixed" ? t("timingFixedHelp") : t("timingFlexibleHelp")}</span></div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldRepeats")}</span>
        <Segmented label={t("fieldRepeats")} value={draft.repeatKind} onChange={(repeatKind) => set({ repeatKind })}
          options={[["none", t("repeatNone")], ["daily", t("flagDaily")], ["weekly", t("flagWeekly")]]} /></div>
      <label className="dw-switch">
        <input type="checkbox" role="switch" checked={draft.protected} onChange={(event) => set({ protected: event.target.checked })} />
        <span><strong>{t("flagProtected")}</strong><span className="dw-caption">{t("protectedLine")}</span></span>
      </label>
      <label className="dw-field"><span>{t("fieldGoal")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <select value={draft.goalId} onChange={(event) => set({ goalId: event.target.value })}>
          <option value="">{t("noGoalOption")}</option>
          {goalsHere.map((goal) => <option key={goal.id} value={goal.id}>{demoText(goal.title)}</option>)}
        </select></label>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-actions">
        <button type="submit" className="dw-button dw-button-primary" disabled={!canSave}>{saving ? t("savingLabel") : t("saveTask")}</button>
        <button type="button" className="dw-button dw-button-quiet" onClick={onCancel}>{t("cancel")}</button>
      </div>
      {!backendConnected && <p className="dw-caption">{t("previewCannotSave")}</p>}
    </form>
  );
}

/**
 * One row's details: what it is, its status, and Edit and Remove. Removal takes two steps and says
 * plainly when it is refused; a set plan's entry is refused at once, since a set plan stays as set.
 * @param {object} props
 * @param {object} props.row - The row on show.
 * @param {object|null} props.task - The stored task behind the row, if it has one.
 * @param {object[]} props.goals - The user's goals, to name a linked one.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report the row's status.
 * @param {() => void} props.onEdit - Edit the task.
 * @param {(item: object) => Promise<void>} props.onRemove - Remove the task.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {() => void} props.onClose - Close the sheet.
 */
function TaskDetail({ row, task, goals, backendConnected, onStatus, onEdit, onRemove, onReplace, onClose }) {
  const { t, language, demoText } = useI18n();
  const [step, setStep] = useState("view");
  const [refusal, setRefusal] = useState("");
  const removeRef = useRef(null);
  const leftView = useRef(false);
  const goal = goals.find((candidate) => candidate.id === task?.goalId);
  const fromPlan = row.kind === "entry";

  useEffect(() => {
    if (step !== "view") leftView.current = true;
    else if (leftView.current) removeRef.current?.focus();
  }, [step]);

  async function remove() {
    try {
      await onRemove(task);
      onClose();
    } catch (caught) {
      setRefusal(caught.message);
      setStep("refused");
    }
  }

  return (
    <div className="dw-detail">
      <p className="dw-row-title"><AreaTag domain={row.domain} /><span className="dw-heading">{demoText(row.title)}</span></p>
      <p className="dw-muted">{timeRange(row.start_time, row.duration_minutes)} · {formatMinutes(row.duration_minutes, language)}</p>
      {row.detail && <p className="dw-muted">{demoText(row.detail)}</p>}
      {row.outsidePlan && <p className="dw-row-note"><Icon name="info" size={16} />{t("notInSetPlan")}</p>}
      <p className="dw-row-flags">
        {row.constraint_kind === "fixed" && <span><Icon name="pin" size={16} />{t("flagFixed")}</span>}
        {Boolean(task?.protected) && <span><Icon name="shield" size={16} />{t("flagProtected")}</span>}
        {task?.repeatKind && task.repeatKind !== "none" && <span><Icon name="repeat" size={16} />{t(task.repeatKind === "daily" ? "flagDaily" : "flagWeekly")}</span>}
        {goal && <span><Icon name="link" size={16} />{demoText(goal.title)}</span>}
      </p>
      {task?.originKind === "agent-origin" && (
        <p className="dw-evidence dw-pencilled"><Icon name="agent" size={16} /><span>{t("agentOrigin")} · {demoText(task.originDetail)}</span></p>
      )}
      <p className="dw-label">{t("reportWhatHappened")}</p>
      <StatusControl variant="segmented" value={row.completion_status} title={demoText(row.title)} disabled={!backendConnected}
        onChange={(status) => onStatus(row, status)} />

      {task && step === "view" && (
        <div className="dw-actions dw-detail-actions">
          <button type="button" className="dw-button" disabled={!backendConnected} onClick={onEdit}><Icon name="pencil" size={18} />{t("editAction")}</button>
          <button type="button" ref={removeRef} className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setStep(fromPlan ? "refused" : "confirm")}><Icon name="trash" size={18} />{t("removeEllipsis")}</button>
        </div>
      )}
      {step === "confirm" && (
        <div className="dw-confirm-remove" role="alertdialog" aria-labelledby="dw-remove-title" aria-describedby="dw-remove-body">
          <p className="dw-step">{t("stepTwoOfTwo")}</p>
          <h3 id="dw-remove-title">{t("removeTaskQuestion")} “{demoText(row.title)}”?</h3>
          <p id="dw-remove-body">{t("removeTaskConsequence")}</p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-danger" onClick={remove}><Icon name="trash" size={18} />{t("removeTaskAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setStep("view")}>{t("cancel")}</button>
          </div>
        </div>
      )}
      {step === "refused" && (
        <div className="dw-refusal" role="alert">
          <h3>{t("cantRemoveTask")}</h3>
          <p>{fromPlan ? t("setPlanKeepsTask") : refusal}</p>
          <p><strong>{t("nothingWasRemoved")}</strong></p>
          <div className="dw-actions">
            {fromPlan && <button type="button" className="dw-button" autoFocus onClick={() => { onStatus(row, "skipped"); setStep("view"); }}>{t("reportSkipped")}</button>}
            {fromPlan && <button type="button" className="dw-button" onClick={onReplace}>{t("reviewReplacement")}</button>}
            <button type="button" className="dw-button dw-button-quiet" autoFocus={!fromPlan} onClick={() => setStep("view")}>{t("okAction")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
