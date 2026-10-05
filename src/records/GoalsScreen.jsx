import { useEffect, useRef, useState } from "react";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { goalLinks, libraryOf } from "../library/libraryData";
import { LibraryItemList } from "../library/SourceList";
import { AreaTag, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { formatMinutes, fullDate } from "../time";
import { goalSpan } from "./goalSpan";
import { cardTasks, goalTaskAction, stillLinkedKeys } from "./goalTasks";
import { SheetForm } from "./SheetForm";

/** Goal states, each with the line that explains what it means for plans. */
const GOAL_STATES = [["active", "goalActiveHelp"], ["paused", "goalPausedHelp"], ["completed", "goalCompletedHelp"]];

/**
 * One task in a goal's sheet. A task today or later has Edit. A past task is history, with a lock
 * and its status as text, and has only Delete, in two steps; a plan set for its day keeps its
 * entry. A refusal from the local service shows in its place.
 * @param {object} props
 * @param {object} props.item - The linked task.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(item: object) => void} props.onEdit - Edit the task.
 * @param {(item: object) => Promise<void>} props.onDelete - Delete the task.
 */
function GoalTask({ item, today, backendConnected, onEdit, onDelete }) {
  const { t, language, demoText } = useI18n();
  const [step, setStep] = useState("view");
  const [refusal, setRefusal] = useState("");
  const title = demoText(item.title);
  const past = goalTaskAction(item, today) === "delete";

  /** Delete the task; a refusal from the local service is shown in its place. */
  async function remove() {
    try {
      await onDelete(item);
    } catch (caught) {
      setRefusal(caught.message);
      setStep("refused");
    }
  }

  return (
    <li className={past ? "dw-goal-task-past" : undefined}>
      <Icon name={past ? "lock" : `status-${item.status}`} size={16} label={past ? t("pastTaskLabel") : undefined} />
      <span className="dw-goal-task-text"><span className="dw-goal-task-title">{title}</span>
        <span className="dw-caption">{whenOf(item, today, language, t)} · {t(item.status)}</span></span>
      {past ? (
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || step !== "view"}
          aria-label={t("deleteTaskNamed", { title })} onClick={() => setStep("confirm")}>
          <Icon name="trash" size={16} />{t("deleteEllipsis")}</button>
      ) : (
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
          aria-label={t("editTaskNamed", { title })} onClick={() => onEdit(item)}>
          <Icon name="pencil" size={16} />{t("editAction")}</button>
      )}
      {step === "confirm" && (
        <div className="dw-confirm-remove" role="alertdialog" aria-labelledby={`dw-delete-${item.id}`} aria-describedby={`dw-delete-${item.id}-body`}>
          <p className="dw-step">{t("stepTwoOfTwo")}</p>
          <h3 id={`dw-delete-${item.id}`}>{t("deletePastTaskQuestion", { title })}</h3>
          <p id={`dw-delete-${item.id}-body`}>{t("deletePastTaskConsequence")}</p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-danger" onClick={remove}><Icon name="trash" size={18} />{t("deleteTaskAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setStep("view")}>{t("cancel")}</button>
          </div>
        </div>
      )}
      {step === "refused" && (
        <div className="dw-refusal" role="alert">
          <h3>{t("cantRemoveTask")}</h3>
          <p>{refusal}</p>
          <p><strong>{t("nothingWasRemoved")}</strong></p>
          <div className="dw-actions">
            <button type="button" className="dw-button" autoFocus onClick={() => { setRefusal(""); setStep("view"); }}>{t("okAction")}</button>
          </div>
        </div>
      )}
    </li>
  );
}

/**
 * Create a goal, or rename one. A goal's area is fixed once it exists, because its linked tasks
 * belong to that area. Editing a goal shows its area and the time it spans side by side, then every
 * task in it with its total length: a task today or later has Edit, which opens its form in place of
 * this sheet until it closes, and a past one has Delete, as it changes only through Ava. Last comes
 * the goal's Library, with Add note or file, which opens the Library's add sheet linked to the goal
 * in place of this one until it closes.
 * @param {object} props
 * @param {object|null} props.goal - The goal to rename, or null for a new one.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {boolean} props.hidden - Whether a sheet it opened is on show instead.
 * @param {boolean} props.atTasks - Open at the goal's task list rather than its title.
 * @param {object[]|null} props.library - The Library's notes and files, newest first; null until they load.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSave - Save the goal.
 * @param {(item: object) => void} props.onEditTask - Edit one of the goal's tasks.
 * @param {(item: object) => Promise<void>} props.onDeleteTask - Delete one of the goal's past tasks.
 * @param {(links: {domain: string, goalId: string}) => void} props.onAddToLibrary - Add a note or file linked to the goal.
 * @param {() => void} props.onClose - Close the sheet.
 * @param {string} [props.defaultDomain="learning"] - A new goal's area until another is chosen, as an area's screen starts it in its own.
 */
export function GoalSheet({ goal, today, backendConnected, hidden, atTasks, library, onSave, onEditTask, onDeleteTask, onAddToLibrary, onClose,
  defaultDomain = "learning" }) {
  const { t, language } = useI18n();
  const linked = goal?.linkedItems || [];
  const kept = goal && library ? libraryOf(library, { goalId: goal.id }) : [];
  const [title, setTitle] = useState(goal?.title || "");
  const [domain, setDomain] = useState(goal?.domain || defaultDomain);
  const tasksRef = useRef(null);

  // Opened to show the tasks that keep the goal from being removed: start there.
  useEffect(() => {
    if (!atTasks) return;
    tasksRef.current?.scrollIntoView({ block: "start" });
    tasksRef.current?.focus();
  }, [atTasks]);

  /**
   * Delete a past task, then keep keyboard focus in the list it left.
   * @param {object} item - The task.
   */
  async function deleteTask(item) {
    await onDeleteTask(item);
    tasksRef.current?.focus();
  }

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
            <h3 className="dw-section-label" ref={tasksRef} tabIndex={-1}>{t("goalTasksHeading", { count: linked.length })}</h3>
            {linked.length > 0 && <span className="dw-caption">{formatMinutes(goal.taskMinutes, language)}</span>}
          </div>
          {linked.length ? (
            <ul className="dw-goal-task-list">
              {linked.map((item) => (
                <GoalTask key={item.id} item={item} today={today} backendConnected={backendConnected}
                  onEdit={onEditTask} onDelete={deleteTask} />
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noLinkedTasks")}</p>}
          {linked.some((item) => goalTaskAction(item, today) === "delete") && <p className="dw-caption">{t("goalPastTaskNote")}</p>}
        </section>
      )}
      {goal && (
        <section className="dw-goal-sheet-library" aria-labelledby="dw-goal-library">
          <h3 id="dw-goal-library" className="dw-section-label">{t("librarySection")} <span className="dw-caption">{kept.length}</span></h3>
          {kept.length ? <LibraryItemList items={kept} /> : <p className="dw-muted">{t("goalLibraryEmpty")}</p>}
          <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => onAddToLibrary(goalLinks(goal))}>
            <Icon name="plus" size={18} />{t("addToLibraryFromGoal")}</button>
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
 * One goal: its area and status, how far reported work has taken it, up to 3 of the tasks linked to
 * it (see cardTasks), with Show all for more, and Edit, Remove and Add task. Every card keeps room
 * for 3 tasks, so cards are the same height with their buttons in line. Removal takes two steps,
 * and is refused while tasks still link to it.
 * @param {object} props
 * @param {object} props.goal - The goal.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(status: string) => void} props.onStatus - Change the goal's status.
 * @param {() => void} props.onEdit - Rename the goal.
 * @param {() => Promise<void>} props.onRemove - Remove the goal.
 * @param {() => void} props.onAddTask - Add a task linked to the goal.
 * @param {() => void} props.onShowTasks - Open the goal's sheet at its linked tasks.
 */
function GoalCard({ goal, today, backendConnected, onStatus, onEdit, onRemove, onAddTask, onShowTasks }) {
  const { t, language, demoText } = useI18n();
  const [step, setStep] = useState("view");
  const linked = goal.linkedItems || [];
  const listed = cardTasks(linked, today);
  const stillLinked = stillLinkedKeys(linked.length);
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
      <div className="dw-goal-tasks">
        {linked.length ? (
          <ul className="dw-goal-links">
            {listed.shown.map((item) => (
              <li key={item.id}><Icon name="link" size={16} /><span>{demoText(item.title)}</span>
                <span className="dw-caption">{whenOf(item, today, language, t)}</span></li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("noLinkedTasks")}</p>}
        {listed.more && <button type="button" className="dw-link dw-goal-show-all" onClick={onShowTasks}>{t("goalShowAll", { count: listed.total })}</button>}
      </div>

      {step === "refused" && (
        <div className="dw-refusal" role="alert">
          <h3><Icon name="alert" size={18} /> {t("cantRemoveGoal")}</h3>
          <p>{t(stillLinked.body, { count: linked.length })}</p>
          <p><strong>{t("nothingWasRemoved")}</strong></p>
          <div className="dw-actions">
            <button type="button" className="dw-button" autoFocus onClick={() => { setStep("view"); onShowTasks(); }}><Icon name="arrow" size={18} />{t(stillLinked.action, { count: linked.length })}</button>
            <button type="button" className="dw-button" onClick={() => setStep("view")}>{t("okAction")}</button>
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
 * @param {object[]|null} props.library - The Library's notes and files, newest first; null until they load.
 * @param {(goal: object) => void} props.onAddTask - Add a task linked to a goal.
 * @param {(links: {domain: string, goalId: string}) => void} props.onAddToLibrary - Add a note or file linked to a goal.
 * @param {boolean} props.sheetOpen - Whether a task's sheet, the Library's add sheet or the Guide's is open, which the goal's sheet waits behind.
 * @param {(item: object) => void} props.onEditTask - Open one of a goal's tasks in its form.
 * @param {(item: object) => Promise<void>} props.onRemoveTask - Delete one of a goal's past tasks.
 * @param {(screen: string) => void} props.onGuide - Open the Goals card from the Guide.
 */
export function GoalsScreen({ day, today, backendConnected, library, onSaveGoal, onRemoveGoal, onAddTask, onAddToLibrary, sheetOpen, onEditTask,
  onRemoveTask, onGuide }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState(undefined);
  const [atTasks, setAtTasks] = useState(false);

  /**
   * Open a goal's sheet, or a new goal's.
   * @param {object|null} goal - The goal, or null for a new one.
   * @param {boolean} [tasks=false] - Open it at the goal's task list.
   */
  function openGoal(goal, tasks = false) {
    setAtTasks(tasks);
    setEditing(goal);
  }
  const goals = day.goals;
  // The goal as it is now, so its tasks show any edit made from its sheet.
  const editingGoal = editing && (goals.find((goal) => goal.id === editing.id) || editing);
  const shown = filter === "all" ? goals : goals.filter((goal) => goal.status === filter);
  const count = (status) => goals.filter((goal) => goal.status === status).length;

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <div className="dw-title-guide">
            <h1 className="dw-display">{t("goalsTitle")}</h1>
            <GuideButton screen="goals" onOpen={onGuide} />
          </div>
          <Segmented label={t("goalsFilter")} value={filter} onChange={setFilter}
            options={[["all", `${t("filterAll")} · ${goals.length}`], ...GOAL_STATES.map(([status]) => [status, `${t(status)} · ${count(status)}`])]} />
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={() => openGoal(null)}><Icon name="plus" size={18} />{t("newGoalAction")}</button>
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
              onEdit={() => openGoal(goal)} onRemove={() => onRemoveGoal(goal)}
              onAddTask={() => onAddTask(goal)} onShowTasks={() => openGoal(goal, true)} />
          ))}
        </div>
      )}
      </div>
      {editing !== undefined && (
        <GoalSheet key={editing?.id || "new"} goal={editingGoal} today={today} backendConnected={backendConnected} hidden={sheetOpen}
          atTasks={atTasks} library={library} onSave={onSaveGoal} onEditTask={onEditTask} onDeleteTask={onRemoveTask}
          onAddToLibrary={onAddToLibrary} onClose={() => setEditing(undefined)} />
      )}
    </main>
  );
}
