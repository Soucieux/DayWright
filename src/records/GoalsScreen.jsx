import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { formatMinutes, fullDate } from "../time";
import { goalSpan } from "./goalSpan";
import { SheetForm } from "./SheetForm";

/** Goal states, each with the line that explains what it means for plans. */
const GOAL_STATES = [["active", "goalActiveHelp"], ["paused", "goalPausedHelp"], ["completed", "goalCompletedHelp"]];

/**
 * Create a goal, or rename one. A goal's area is fixed once it exists, because its linked tasks
 * belong to that area. Editing a goal shows its area and the time it spans side by side, then every
 * task in it with its total length, each with Edit, whatever its status and on whatever day: Edit
 * opens the task's form in place of this sheet until it closes.
 * @param {object} props
 * @param {object|null} props.goal - The goal to rename, or null for a new one.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {boolean} props.hidden - Whether a task it opened is on show instead.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSave - Save the goal.
 * @param {(item: object) => void} props.onEditTask - Edit one of the goal's tasks.
 * @param {() => void} props.onClose - Close the sheet.
 */
function GoalSheet({ goal, today, backendConnected, hidden, onSave, onEditTask, onClose }) {
  const { t, language, demoText } = useI18n();
  const linked = goal?.linkedItems || [];
  const [title, setTitle] = useState(goal?.title || "");
  const [domain, setDomain] = useState(goal?.domain || "learning");
  return (
    <SheetForm title={goal ? t("editGoalTitle") : t("newGoalTitle")} submitLabel={t("saveGoal")} backendConnected={backendConnected} hidden={hidden}
      onSubmit={() => onSave(goal?.id || null, goal ? { title: title.trim(), status: goal.status } : { title: title.trim(), domain })} onClose={onClose}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={title}
          onInvalid={(event) => event.target.setCustomValidity(t("goalTitleNeeded"))}
          onChange={(event) => { event.target.setCustomValidity(""); setTitle(event.target.value); }} /></label>
      {goal ? (
        <dl className="dw-goal-facts">
          <div><dt>{t("fieldArea")}</dt>
            <dd><AreaTag domain={goal.domain} /><span className="dw-caption">{t("goalAreaFixed")}</span></dd></div>
          <div><dt>{t("goalSpanLabel")}</dt>
            <dd><span className="dw-goal-span"><Icon name="clock" size={16} /><span>{goalSpan(goal, t, language)}</span></span>
              <span className="dw-caption">{t("goalSpanNote")}</span></dd></div>
        </dl>
      ) : (
        <div className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
          <Segmented label={t("fieldArea")} value={domain} onChange={setDomain}
            options={DOMAINS.map((value) => [value, <AreaTag key={value} domain={value} plain />])} /></div>
      )}
      {goal && (
        <section className="dw-goal-sheet-tasks">
          <div className="dw-goal-sheet-tasks-head">
            <h3 className="dw-section-label">{t("goalTasksHeading", { count: linked.length })}</h3>
            {linked.length > 0 && <span className="dw-caption">{formatMinutes(goal.taskMinutes, language)}</span>}
          </div>
          {linked.length ? (
            <ul className="dw-goal-task-list">
              {linked.map((item) => (
                <li key={item.id}>
                  <Icon name={`status-${item.status}`} size={16} />
                  <span className="dw-goal-task-text"><span className="dw-goal-task-title">{demoText(item.title)}</span>
                    <span className="dw-caption">{whenOf(item, today, language, t)} · {t(item.status)}</span></span>
                  <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
                    aria-label={t("editTaskNamed", { title: demoText(item.title) })} onClick={() => onEditTask(item)}>
                    <Icon name="pencil" size={16} />{t("editAction")}</button>
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noLinkedTasks")}</p>}
        </section>
      )}
    </SheetForm>
  );
}

/**
 * Name when a linked task happens: today, or its weekday and day, with its time when it has one.
 * @param {object} item - The linked task, with `date` and `startTime`, which is null for a flexible task.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} Such as "Today 17:30" or "Thursday 24 September".
 */
function whenOf(item, today, language, t) {
  const day = item.date === today ? t("navToday") : fullDate(item.date, language);
  return item.startTime ? `${day} ${item.startTime}` : day;
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
    <article className={`dw-card dw-goal-card dw-area-${areaOf(goal.domain)}`} aria-labelledby={`dw-goal-${goal.id}`}>
      <div className="dw-card-head">
        <AreaTag domain={goal.domain} />
        <MenuSelect variant="compact" label={t("goalStatusFor", { title })} value={goal.status}
          buttonLabel={`${t("goalStatusFor", { title })}: ${t(goal.status)}`} disabled={!backendConnected} onChange={onStatus}
          options={GOAL_STATES.map(([status, help]) => ({ value: status, label: t(status), note: t(help) }))} />
      </div>
      <h2 id={`dw-goal-${goal.id}`} className="dw-heading">{title}</h2>
      <p className="dw-goal-span"><Icon name="clock" size={16} /><span>{goalSpan(goal, t, language)}</span></p>
      {goal.status === "paused" && <p className="dw-row-note dw-row-paused-note"><Icon name="pause" size={16} />{t("goalPausedTasks")}</p>}
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
        <button type="button" className="dw-button" disabled={!backendConnected || step !== "view"}
          onClick={() => setStep(linked.length ? "refused" : "confirm")}><Icon name="trash" size={18} />{t("removeEllipsis")}</button>
        <span className="dw-spacer" />
        <button type="button" className="dw-button" disabled={!backendConnected || goal.status !== "active"} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
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
 * @param {boolean} props.taskOpen - Whether a task's sheet is open, which the goal's sheet waits behind.
 * @param {(item: object) => void} props.onEditTask - Open one of a goal's tasks in its form.
 */
export function GoalsScreen({ day, today, backendConnected, onSaveGoal, onRemoveGoal, onAddTask, onShowTasks, taskOpen, onEditTask }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState(undefined);
  const goals = day.goals;
  // The goal as it is now, so its tasks show any edit made from its sheet.
  const editingGoal = editing && (goals.find((goal) => goal.id === editing.id) || editing);
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
      <div className="dw-page-body">
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
      </div>
      {editing !== undefined && (
        <GoalSheet key={editing?.id || "new"} goal={editingGoal} today={today} backendConnected={backendConnected} hidden={taskOpen}
          onSave={onSaveGoal} onEditTask={onEditTask} onClose={() => setEditing(undefined)} />
      )}
    </main>
  );
}
