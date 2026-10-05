import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Segmented } from "../ui/Segmented";
import { Sheet } from "../ui/Sheet";
import { StatusControl } from "../ui/StatusControl";
import { agentName } from "../ui/agentName";
import { timeRange } from "../time";
import { AREA_MEANINGS } from "./areaOverview";
import { MIN_TASK_MINUTES, linkableGoals, newTaskDate, suggestsArea, taskDraft, taskLength, taskPayload } from "./taskDraft";
import { firstFreeStart, startClash, startOptions, timedTasks } from "./taskTimes";
import { refusalKey } from "../serviceText";
import { useDayTasks } from "./useDayTasks";

/** How long the task form waits after the title or detail last changed before asking for an area, in milliseconds. */
const SUGGEST_DELAY_MS = 500;

/**
 * The task sheet: a form for a new task, or a task's details with Edit and Remove.
 * @param {object} props
 * @param {object|null} props.row - The row whose details to show, or null to record a new task.
 * @param {string} props.date - The day on show; a new task starts on it when it is later than today.
 * @param {string} props.today - Today's YYYY-MM-DD date, the earliest a new task can be set for; a
 *   task already recorded may stay on, or move to, any day, past ones included.
 * @param {object[]} props.goals - The user's goals.
 * @param {{domain?: string, goalId?: string}} [props.defaults] - A new task's area and goal, when it is added from one.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(payload: object, itemId: string|null) => Promise<void>} props.onSave - Save a task.
 * @param {(item: object) => Promise<void>} props.onRemove - Remove a task.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {() => void} props.onClose - Close the sheet.
 * @param {boolean} [props.startEditing=false] - Open straight into the task's form, as a goal's
 *   sheet does, and close once the form is saved or cancelled.
 */
export function TaskSheet({ row, date, today, goals, defaults, backendConnected, onSave, onRemove, onStatus, onReplace, onClose, startEditing = false }) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(!row || startEditing);
  const task = row?.source || null;
  if (editing) {
    const back = task && !startEditing ? () => setEditing(false) : onClose;
    return (
      <Sheet title={task ? t("editTaskTitle") : t("newTaskTitle")} view="form" onClose={onClose}>
        <TaskForm task={task} date={newTaskDate(date, today)} today={today} goals={goals} defaults={defaults} backendConnected={backendConnected} onSave={onSave}
          onDone={back} onCancel={back} />
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
 * @param {string} props.date - The date a new task starts on; the user may change it.
 * @param {string} props.today - Today's YYYY-MM-DD date, the earliest a new task can be set for; a
 *   task already recorded may stay on, or move to, any day, past ones included.
 * @param {object[]} props.goals - The user's goals.
 * @param {{domain?: string, goalId?: string}} [props.defaults] - A new task's area and goal, when it is added from one.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(payload: object, itemId: string|null) => Promise<void>} props.onSave - Save the task.
 * @param {() => void} props.onDone - Called after a successful save.
 * @param {() => void} props.onCancel - Leave without saving.
 */
function TaskForm({ task, date, today, goals, defaults, backendConnected, onSave, onDone, onCancel }) {
  const { t, demoText } = useI18n();
  const [draft, setDraft] = useState(() => taskDraft(task, date, defaults?.domain, defaults?.goalId));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  // The area the Orchestrator suggested, until the user picks one themselves.
  const [picked, setPicked] = useState(false);
  const [suggested, setSuggested] = useState(null);
  const { tasks: dayTasks, meals } = useDayTasks(draft.date, backendConnected);
  const set = (fields) => setDraft((current) => ({ ...current, ...fields }));
  const asking = backendConnected && suggestsArea(task, defaults, draft, picked);

  useEffect(() => {
    if (!asking) return undefined;
    let live = true;
    const timer = setTimeout(() => {
      api("/api/areas/suggest", { method: "POST", body: JSON.stringify({ title: draft.title, detail: draft.detail }) })
        .then((answer) => {
          if (!live) return;
          setSuggested(answer.domain);
          set({ domain: answer.domain });
        })
        // Without a suggestion the area stays as it is; the user chooses it either way.
        .catch(() => {});
    }, SUGGEST_DELAY_MS);
    return () => { live = false; clearTimeout(timer); };
  }, [asking, draft.title, draft.detail]);
  const goalsHere = linkableGoals(goals, draft.domain, task?.goalId || "");
  // A fixed task's start may not overlap another task on its day, for as long as it lasts; without
  // a length given, it lasts its estimate, or the area agent's usual first estimate.
  const timed = timedTasks(dayTasks, task?.id || null);
  const estimate = task?.durationSource === "estimate" ? task.duration_minutes : null;
  const minutes = Number(draft.durationMinutes) || estimate || MIN_TASK_MINUTES;
  const clash = draft.constraintKind === "fixed" ? startClash(draft.startTime, minutes, timed, meals) : null;
  const canSave = backendConnected && !saving && !clash;

  /** Switch between flexible and fixed; a fixed task starts at a free time when its own is taken. */
  function setTiming(constraintKind) {
    const free = constraintKind === "fixed" && startClash(draft.startTime, minutes, timed, meals)
      ? firstFreeStart(draft.startTime, minutes, timed, meals) : null;
    set({ constraintKind, ...(free ? { startTime: free } : {}) });
  }

  async function submit(event) {
    event.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError("");
    try {
      await onSave(taskPayload(draft), task?.id || null);
      onDone();
    } catch (caught) {
      const key = refusalKey(caught.message);
      setError(key ? t(key) : caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="dw-form" onSubmit={submit}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={draft.title}
          onInvalid={(event) => event.target.setCustomValidity(t("titleNeeded"))}
          onChange={(event) => { event.target.setCustomValidity(""); set({ title: event.target.value }); }} /></label>
      <label className="dw-field"><span>{t("fieldDetail")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <textarea maxLength={1000} rows={2} value={draft.detail} onChange={(event) => set({ detail: event.target.value })} /></label>
      <label className="dw-field">{t("fieldDate")}
        <input type="date" required min={today} value={draft.date} onChange={(event) => set({ date: event.target.value })} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
        <Segmented label={t("fieldArea")} value={draft.domain} onChange={(domain) => { setPicked(true); set({ domain, goalId: "" }); }}
          options={DOMAINS.map((domain) => [domain, <AreaTag key={domain} domain={domain} plain />])} />
        {suggested && !picked && suggested === draft.domain && (
          <p className="dw-evidence dw-pencilled"><Icon name="agent" size={16} />
            <span>{t("areaSuggested", { agent: agentName("orchestrator", t), area: t(suggested) })}</span></p>
        )}
        <span className="dw-caption">{t("areaRuleNote")}</span>
        <ul className="dw-area-meanings">
          {Object.entries(AREA_MEANINGS).map(([domain, key]) => (
            <li key={domain} className={draft.domain === domain ? "dw-area-meaning-on" : undefined}>
              <AreaGlyph domain={domain} /><span><strong>{t(domain)}</strong> · {t(key)}</span></li>
          ))}
        </ul></div>
      <div className="dw-field" role="group" aria-labelledby="dw-timing-label"><span id="dw-timing-label" className="dw-field-label">{t("fieldTiming")}</span>
        <Segmented label={t("fieldTiming")} value={draft.constraintKind} onChange={setTiming}
          options={[["flexible", t("timingFlexible")], ["fixed", t("flagFixed")]]} />
        <span className="dw-caption">{draft.constraintKind === "fixed" ? t("timingFixedHelp") : t("timingFlexibleHelp")}</span>
        <div className="dw-field-row">
          {draft.constraintKind === "fixed" && <div className="dw-field"><span className="dw-field-label">{t("fieldStart")}</span>
            <MenuSelect label={t("fieldStart")} value={draft.startTime} describedBy={clash ? "dw-start-clash" : undefined}
              onChange={(startTime) => set({ startTime })}
              options={startOptions(minutes, timed, draft.startTime, meals).map(({ time, clash: taken }) => ({
                value: time, label: time, disabled: Boolean(taken) && time !== draft.startTime,
                note: !taken ? undefined : taken.midnight ? t("startPastMidnight")
                  : taken.meal ? t("startMeal", { meal: t(`meal${taken.meal.title}`) }) : t("startTaken", { title: demoText(taken.task.title) }),
              }))} /></div>}
          <label className="dw-field"><span>{t("fieldDuration")} <span className="dw-optional">{t("optionalLabel")}</span></span>
            <input type="number" min={MIN_TASK_MINUTES} max={1440} value={draft.durationMinutes}
              placeholder={estimate ? `≈ ${estimate}` : ""}
              onInvalid={(event) => event.target.setCustomValidity(t("durationMinimum", { minutes: MIN_TASK_MINUTES }))}
              onChange={(event) => { event.target.setCustomValidity(""); set({ durationMinutes: event.target.value }); }} /></label>
        </div>
        <span className="dw-caption">{t("durationOptionalHelp", { minutes: MIN_TASK_MINUTES, agent: agentName(draft.domain, t) })}</span>
        {clash && (
          <p id="dw-start-clash" className="dw-alert" role="alert">
            {clash.midnight ? t("startClashMidnight")
              : clash.meal ? t("startClashMeal", { time: draft.startTime, meal: t(`meal${clash.meal.title}`), range: timeRange(clash.meal.start_time, clash.meal.duration_minutes) })
                : t("startClash", { time: draft.startTime, title: demoText(clash.task.title), range: timeRange(clash.task.start_time, clash.task.duration_minutes) })}
          </p>
        )}</div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldRepeats")}</span>
        <Segmented label={t("fieldRepeats")} value={draft.repeatKind} onChange={(repeatKind) => set({ repeatKind })}
          options={[["none", t("repeatNone")], ["daily", t("flagDaily")], ["weekly", t("flagWeekly")]]} /></div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldGoal")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <MenuSelect label={t("fieldGoal")} value={draft.goalId} onChange={(goalId) => set({ goalId })}
          options={[{ value: "", label: t("noGoalOption") }, ...goalsHere.map((goal) => ({ value: goal.id, label: demoText(goal.title) }))]} /></div>
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
      <p className="dw-muted">{row.start_time ? timeRange(row.start_time, row.duration_minutes) : t("noStartTime")} · {taskLength(row, language)}</p>
      {task?.durationSource === "estimate" && <p className="dw-caption">{t("estimatedByAgent", { agent: agentName(task.estimatedBy || task.domain, t) })}</p>}
      {row.detail && <p className="dw-muted">{demoText(row.detail)}</p>}
      {row.outsidePlan && <p className="dw-row-note"><Icon name="info" size={16} />{t("notInSetPlan")}</p>}
      <p className="dw-row-flags">
        {row.constraint_kind === "fixed" && <span><Icon name="pin" size={16} />{t("flagFixed")}</span>}
        {task?.repeatKind && task.repeatKind !== "none" && <span><Icon name="repeat" size={16} />{t(task.repeatKind === "daily" ? "flagDaily" : "flagWeekly")}</span>}
        {goal && <span><Icon name="link" size={16} />{demoText(goal.title)}</span>}
      </p>
      {task?.originKind === "agent-origin" && (
        <p className="dw-evidence dw-pencilled"><Icon name="agent" size={16} /><span>{t("agentOrigin")} · {demoText(task.originDetail)}</span></p>
      )}
      {task?.goalStatus === "paused" && <p className="dw-row-note dw-row-paused-note"><Icon name="pause" size={16} />{t("taskGoalPaused")}</p>}
      <p className="dw-label">{t("reportWhatHappened")}</p>
      <StatusControl variant="segmented" value={row.completion_status} title={demoText(row.title)} disabled={!backendConnected}
        paused={task?.goalStatus === "paused"} onChange={(status) => onStatus(row, status)} />

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
            {fromPlan && task?.goalStatus !== "paused" && <button type="button" className="dw-button" autoFocus onClick={() => { onStatus(row, "skipped"); setStep("view"); }}>{t("reportSkipped")}</button>}
            {fromPlan && <button type="button" className="dw-button" onClick={onReplace}>{t("reviewReplacement")}</button>}
            <button type="button" className="dw-button" autoFocus={!fromPlan} onClick={() => setStep("view")}>{t("okAction")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
