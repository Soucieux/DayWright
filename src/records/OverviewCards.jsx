import { useI18n } from "../i18n";
import { areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { agentName } from "../ui/agentName";
import { formatMinutes, longDate, shortDate, timeRange } from "../time";
import { carryOverText, loadBars, streakText } from "./areaOverview";

/**
 * The goals an area agent flags, pencilled and named after it: Learning's due for review, or
 * Project's stalled, each with how long nothing has been done toward it.
 * @param {object} props
 * @param {string} props.agent - The area agent's key.
 * @param {string} props.title - The card's heading.
 * @param {{goalId: string, title: string, days: number}[]} props.goals - The goals it flags.
 */
function FlaggedGoals({ agent, title, goals }) {
  const { t, demoText } = useI18n();
  if (!goals.length) return null;
  return (
    <section className="dw-card dw-pencilled" aria-labelledby={`dw-flags-${agent}`}>
      <p className="dw-agent-line"><span className="dw-agent-mark"><Icon name="agent" size={16} /></span>
        <strong id={`dw-flags-${agent}`}>{title}</strong><span className="dw-caption">· {agentName(agent, t)}</span></p>
      <ul className="dw-overview-list">
        {goals.map((goal) => <li key={goal.goalId}><span>{demoText(goal.title)}</span><span className="dw-caption">{t("idleDays", { days: goal.days })}</span></li>)}
      </ul>
    </section>
  );
}

/**
 * Learning: this week's time per goal, when anything was last practised, and the goals due for review.
 * @param {object} props
 * @param {object} props.data - Learning's overview, from the local service.
 */
function LearningOverview({ data }) {
  const { t, language, demoText } = useI18n();
  return (
    <>
      <section className="dw-card" aria-labelledby="dw-learning-week">
        <div className="dw-card-head">
          <h2 id="dw-learning-week" className="dw-heading">{t("learningWeekTitle")}</h2>
          <span className="dw-caption">{data.lastPractised ? t("lastPractisedOn", { date: shortDate(data.lastPractised, language) }) : t("notPractisedYet")}</span>
        </div>
        {data.subjects.length || data.otherMinutes ? (
          <ul className="dw-overview-list">
            {data.subjects.map((subject) => (
              <li key={subject.goalId}><span>{demoText(subject.title)}{subject.status === "paused" && <span className="dw-caption"> · {t("pausedLabel")}</span>}</span>
                <span className="dw-caption">{formatMinutes(subject.minutes, language)}</span></li>
            ))}
            {data.otherMinutes > 0 && <li><span>{t("learningOther")}</span><span className="dw-caption">{formatMinutes(data.otherMinutes, language)}</span></li>}
          </ul>
        ) : <p className="dw-muted">{t("noLearningGoals")}</p>}
      </section>
      <FlaggedGoals agent="learning" title={t("dueForReviewTitle")} goals={data.dueForReview} />
    </>
  );
}

/**
 * Life: its repeats as habits, and the day's appointments, meals, free time and energy.
 * @param {object} props
 * @param {object} props.data - Life's overview, from the local service.
 */
function LifeOverview({ data }) {
  const { t, language, demoText } = useI18n();
  return (
    <>
      <section className="dw-card" aria-labelledby="dw-life-habits">
        <h2 id="dw-life-habits" className="dw-heading dw-card-title">{t("habitsTitle")}</h2>
        {data.habits.length ? (
          <ul className="dw-overview-list">
            {data.habits.map((habit) => (
              <li key={habit.seriesId}>
                <span>{demoText(habit.title)} <span className="dw-row-flags"><span><Icon name="repeat" size={16} />{t(habit.kind === "weekly" ? "flagWeekly" : "flagDaily")}</span></span></span>
                <span className="dw-caption">{t("doneThisWeek", { count: habit.doneThisWeek })} · {streakText(habit, t)}</span>
              </li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("noHabitsRepeats")}</p>}
      </section>
      <section className="dw-card" aria-labelledby="dw-life-day">
        <div className="dw-card-head">
          <h2 id="dw-life-day" className="dw-heading">{longDate(data.date, language).weekday}</h2>
          <span className="dw-caption">{t("energyLabel")}: {data.energy ? t("energyOf", { level: data.energy }) : t("notReportedShort")}</span>
        </div>
        <ul className="dw-overview-list">
          {data.appointments.map((item) => (
            <li key={item.id}><span>{demoText(item.title)}</span><span className="dw-caption">{timeRange(item.start_time, item.duration_minutes)}</span></li>
          ))}
          {!data.appointments.length && <li><span className="dw-muted">{t("noAppointments")}</span></li>}
          {data.meals.map((meal) => (
            <li key={meal.title}><span><Icon name="meal" size={16} /> {t(`mealName${meal.title}`)}</span>
              <span className="dw-caption">{timeRange(meal.start_time, meal.duration_minutes)}</span></li>
          ))}
          <li><span>{t("freeTimeLabel")}</span><span className="dw-caption">{formatMinutes(data.freeMinutes, language)}</span></li>
        </ul>
      </section>
    </>
  );
}

/**
 * Work: the week's load by day, the day's meetings, and what was carried over from the week before.
 * @param {object} props
 * @param {object} props.data - Work's overview, from the local service.
 */
function WorkOverview({ data }) {
  const { t, language, demoText } = useI18n();
  const narrow = new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "narrow" });
  return (
    <>
      <section className="dw-card" aria-labelledby="dw-work-week">
        <h2 id="dw-work-week" className="dw-heading dw-card-title">{t("workWeekTitle")}</h2>
        <ol className={`dw-load-bars dw-area-${areaOf("work")}`}>
          {loadBars(data.load).map((day) => (
            <li key={day.date} className={day.date === data.date ? "dw-load-today" : undefined}
              aria-label={`${longDate(day.date, language).weekday}: ${formatMinutes(day.minutes, language)}`}>
              <span className="dw-load-bar" aria-hidden="true"><span style={{ height: `${Math.round(day.share * 100)}%` }} /></span>
              <span className="dw-caption" aria-hidden="true">{narrow.format(new Date(`${day.date}T12:00:00`))}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="dw-card" aria-labelledby="dw-work-meetings">
        <h2 id="dw-work-meetings" className="dw-heading dw-card-title">{t("meetingsTitle")}</h2>
        {data.meetings.length ? (
          <ul className="dw-overview-list">
            {data.meetings.map((item) => (
              <li key={item.id}><span>{demoText(item.title)}</span><span className="dw-caption">{timeRange(item.start_time, item.duration_minutes)}</span></li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("noMeetings")}</p>}
      </section>
      <section className="dw-card" aria-labelledby="dw-work-carried">
        <h2 id="dw-work-carried" className="dw-heading dw-card-title">{t("carryOversTitle")}</h2>
        {data.carryOvers.length ? (
          <ul className="dw-overview-list">
            {data.carryOvers.map((item) => (
              <li key={`${item.date}-${item.title}`}><span>{demoText(item.title)}</span><span className="dw-caption">{carryOverText(item, t, language)}</span></li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("noCarryOvers")}</p>}
      </section>
    </>
  );
}

/**
 * Project: each project's progress, its last step done and its next one, and the projects that stalled.
 * @param {object} props
 * @param {object} props.data - Project's overview, from the local service.
 * @param {boolean} props.canAdd - Whether a next step can be added now.
 * @param {(goalId: string) => void} props.onAddStep - Add a task to a project's goal.
 */
function ProjectOverview({ data, canAdd, onAddStep }) {
  const { t, language, demoText } = useI18n();
  const step = (key, item) => t(key, { title: demoText(item.title), date: shortDate(item.date, language) });
  return (
    <>
      <section className="dw-card" aria-labelledby="dw-projects">
        <h2 id="dw-projects" className="dw-heading dw-card-title">{t("projectsTitle")}</h2>
        {data.projects.length ? (
          <ul className="dw-overview-steps">
            {data.projects.map((project) => (
              <li key={project.goalId}>
                <p className="dw-overview-step-head"><strong>{demoText(project.title)}</strong>
                  <span className="dw-caption">{project.status === "paused" ? t("pausedLabel") : t("doneOfScheduled", { done: project.done, total: project.total })}</span></p>
                <span className={`dw-track dw-area-${areaOf("project")}`} aria-hidden="true">
                  {project.total > 0 && <span style={{ width: `${Math.round((project.done / project.total) * 100)}%` }} />}
                </span>
                <span className="dw-caption">{project.lastStep ? step("lastStepLabel", project.lastStep) : t("noStepYet")}</span>
                {project.nextStep ? <span className="dw-caption">{step("nextStepLabel", project.nextStep)}</span> : (
                  project.status === "active" && <button type="button" className="dw-button dw-button-quiet" disabled={!canAdd}
                    onClick={() => onAddStep(project.goalId)}><Icon name="plus" size={18} />{t("addNextStep")}</button>
                )}
              </li>
            ))}
          </ul>
        ) : <p className="dw-muted">{t("noProjects")}</p>}
      </section>
      <FlaggedGoals agent="project" title={t("stalledTitle")} goals={data.stalled} />
    </>
  );
}

/**
 * An area's overview of the day on show, built by the local service from its tasks, goals and repeats.
 * @param {object} props
 * @param {"learning"|"life"|"work"|"project"} props.domain - The area.
 * @param {object} props.data - The area's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(defaults: {domain: string, goalId?: string}) => void} props.onAddTask - Record a task in this area.
 */
export function AreaOverview({ domain, data, canAdd, onAddTask }) {
  if (domain === "learning") return <LearningOverview data={data} />;
  if (domain === "life") return <LifeOverview data={data} />;
  if (domain === "work") return <WorkOverview data={data} />;
  return <ProjectOverview data={data} canAdd={canAdd} onAddStep={(goalId) => onAddTask({ domain, goalId })} />;
}
