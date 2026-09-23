import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { fullDate } from "../time";
import { SheetForm } from "./SheetForm";

/** Goal states, each with the line that explains what it means for plans. */
const GOAL_STATES = [["active", "goalActiveHelp"], ["paused", "goalPausedHelp"], ["completed", "goalCompletedHelp"]];

/** Areas a goal can belong to, in the order the area control lists them. */
const GOAL_AREAS = ["learning", "life", "finance", "rest"];

/**
 * Create a goal, or rename one. A goal's area is fixed once it exists, because its linked tasks
 * belong to that area.
 * @param {object} props
 * @param {object|null} props.goal - The goal to rename, or null for a new one.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSave - Save the goal.
 * @param {() => void} props.onClose - Close the sheet.
 */
function GoalSheet({ goal, backendConnected, onSave, onClose }) {
  const { t } = useI18n();
  const [title, setTitle] = useState(goal?.title || "");
  const [domain, setDomain] = useState(goal?.domain || "learning");
  return (
    <SheetForm title={goal ? t("editGoalTitle") : t("newGoalTitle")} submitLabel={t("saveGoal")} backendConnected={backendConnected}
      onSubmit={() => onSave(goal?.id || null, goal ? { title: title.trim(), status: goal.status } : { title: title.trim(), domain })} onClose={onClose}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={title}
          onInvalid={(event) => event.target.setCustomValidity(t("goalTitleNeeded"))}
          onChange={(event) => { event.target.setCustomValidity(""); setTitle(event.target.value); }} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
        {goal
          ? <><AreaTag domain={goal.domain} /><span className="dw-caption">{t("goalAreaFixed")}</span></>
          : <Segmented label={t("fieldArea")} value={domain} onChange={setDomain}
            options={GOAL_AREAS.map((value) => [value, <AreaTag key={value} domain={value} plain />])} />}
      </div>
    </SheetForm>
  );
}

/**
 * Name when a linked task happens: today, or its weekday and day, with its time.
 * @param {object} item - The linked task, with `date` and `startTime`.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} Such as "Today 17:30" or "Thursday 24 September 12:30".
 */
function whenOf(item, today, language, t) {
  return `${item.date === today ? t("navToday") : fullDate(item.date, language)} ${item.startTime}`;
}

/**
 * One goal: its area and status, how far reported work has taken it, the tasks linked to it, and
 * Edit, Remove and Add task. Removal takes two steps, and is refused while tasks still link to it.
 * @param {object} props
 * @param {object} props.goal - The goal.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(status: string) => void} props.onStatus - Change the goal's status.
 * @param {() => void} props.onEdit - Rename the goal.
 * @param {() => Promise<void>} props.onRemove - Remove the goal.
 * @param {() => void} props.onAddTask - Add a task linked to the goal.
 * @param {() => void} props.onShowTasks - List the goal's linked tasks.
 */
function GoalCard({ goal, today, backendConnected, onStatus, onEdit, onRemove, onAddTask, onShowTasks }) {
  const { t, language, demoText } = useI18n();
  const [step, setStep] = useState("view");
  const linked = goal.linkedItems || [];
  const total = Number(goal.itemCount || 0);
  const done = Number(goal.doneCount || 0);
  const title = demoText(goal.title);
  return (
    <article className="dw-card dw-goal-card" aria-labelledby={`dw-goal-${goal.id}`}>
      <div className="dw-card-head">
        <AreaTag domain={goal.domain} />
        <label className="dw-goal-status">
          <span className="dw-visually-hidden">{t("goalStatusFor", { title })}</span>
          <select value={goal.status} disabled={!backendConnected} onChange={(event) => onStatus(event.target.value)}>
            {GOAL_STATES.map(([status, help]) => <option key={status} value={status}>{t(status)} — {t(help)}</option>)}
          </select>
        </label>
      </div>
      <h2 id={`dw-goal-${goal.id}`} className="dw-heading">{title}</h2>
      <span className={`dw-track dw-goal-track dw-area-${areaOf(goal.domain)}`}>
        <span style={{ width: `${total ? Math.round((done / total) * 100) : 0}%` }} />
      </span>
      <p className="dw-goal-progress"><span>{t("goalProgress", { done, total })}</span><span className="dw-caption">{t("reportedNotInferred")}</span></p>
      <h3 className="dw-section-label">{t("linkedTasksHeading", { count: linked.length })}</h3>
      {linked.length ? (
        <ul className="dw-goal-links">
          {linked.map((item) => (
            <li key={item.id}><Icon name="link" size={16} /><span>{demoText(item.title)}</span>
              <span className="dw-caption">{whenOf(item, today, language, t)}</span></li>
          ))}
        </ul>
      ) : <p className="dw-muted">{t("noLinkedTasks")}</p>}

      {step === "refused" && (
        <div className="dw-refusal" role="alert">
          <h3><Icon name="alert" size={18} /> {t("cantRemoveGoal")}</h3>
          <p>{t("goalStillLinked", { count: linked.length })}</p>
          <p><strong>{t("nothingWasRemoved")}</strong></p>
          <div className="dw-actions">
            <button type="button" className="dw-button" autoFocus onClick={onShowTasks}><Icon name="arrow" size={18} />{t("showLinkedTasks", { count: linked.length })}</button>
            <button type="button" className="dw-button dw-button-quiet" onClick={() => setStep("view")}>{t("okAction")}</button>
          </div>
        </div>
      )}
      {step === "confirm" && (
        <div className="dw-confirm-remove" role="alertdialog" aria-labelledby={`dw-remove-${goal.id}`} aria-describedby={`dw-remove-${goal.id}-body`}>
          <p className="dw-step">{t("stepTwoOfTwo")}</p>
          <h3 id={`dw-remove-${goal.id}`}>{t("removeGoalQuestion", { title })}</h3>
          <p id={`dw-remove-${goal.id}-body`}>{t("removeGoalConsequence")}</p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-danger" onClick={() => onRemove().catch(() => setStep("view"))}><Icon name="trash" size={18} />{t("removeGoalAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setStep("view")}>{t("cancel")}</button>
          </div>
        </div>
      )}

      <div className="dw-goal-foot">
        <button type="button" className="dw-button" disabled={!backendConnected} onClick={onEdit}><Icon name="pencil" size={18} />{t("editAction")}</button>
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || step !== "view"}
          onClick={() => setStep(linked.length ? "refused" : "confirm")}><Icon name="trash" size={18} />{t("removeEllipsis")}</button>
        <span className="dw-spacer" />
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || goal.status !== "active"} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
      </div>
    </article>
  );
}

/**
 * The user's goals, filtered by status and laid out as two independent columns. Progress comes only
 * from reported work.
 * @param {object} props
 * @param {object} props.day - The day on show, for its goals and banners.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSaveGoal - Create or update a goal.
 * @param {(goal: object) => Promise<void>} props.onRemoveGoal - Remove a goal.
 * @param {(goal: object) => void} props.onAddTask - Add a task linked to a goal.
 * @param {(goal: object) => void} props.onShowTasks - List a goal's linked tasks.
 */
export function GoalsScreen({ day, today, backendConnected, onSaveGoal, onRemoveGoal, onAddTask, onShowTasks }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState(undefined);
  const goals = day.goals;
  const shown = filter === "all" ? goals : goals.filter((goal) => goal.status === filter);
  const count = (status) => goals.filter((goal) => goal.status === status).length;

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <h1 className="dw-display">{t("goalsTitle")}</h1>
          <Segmented label={t("goalsFilter")} value={filter} onChange={setFilter}
            options={[["all", `${t("filterAll")} · ${goals.length}`], ...GOAL_STATES.map(([status]) => [status, `${t(status)} · ${count(status)}`])]} />
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={() => setEditing(null)}><Icon name="plus" size={18} />{t("newGoalAction")}</button>
        </div>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      <p className="dw-muted dw-page-note">{t("goalsIntroLine")} {t("showingCount", { shown: shown.length, total: goals.length })}</p>
      {goals.length === 0 ? (
        <section className="dw-card dw-empty-card">
          <span className="dw-empty-tile"><Icon name="target" size={24} /></span>
          <h2 className="dw-title">{t("noGoalsYet")}</h2>
          <p className="dw-body-lg">{t("noGoalsBody")}</p>
        </section>
      ) : shown.length === 0 ? <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("noGoalsInFilter")}</p> : (
        <div className="dw-goal-grid">
          {shown.map((goal) => (
            <GoalCard key={goal.id} goal={goal} today={today} backendConnected={backendConnected}
              onStatus={(status) => onSaveGoal(goal.id, { title: goal.title, status }).catch(() => {})}
              onEdit={() => setEditing(goal)} onRemove={() => onRemoveGoal(goal)}
              onAddTask={() => onAddTask(goal)} onShowTasks={() => onShowTasks(goal)} />
          ))}
        </div>
      )}
      {editing !== undefined && (
        <GoalSheet key={editing?.id || "new"} goal={editing} backendConnected={backendConnected} onSave={onSaveGoal} onClose={() => setEditing(undefined)} />
      )}
    </main>
  );
}
