import { useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { formatMinutes, longDate } from "../time";
import { addDays } from "../calendar/month";
import { SheetForm } from "./SheetForm";

/** Mood choices, from the lowest reported value (1) to the highest (5). */
const MOODS = ["moodLow", "moodFlat", "moodSteady", "moodGood", "moodBright"];

/** Energy levels a check-in can report. */
const ENERGY_LEVELS = ["1", "2", "3", "4", "5"];

/** Sleep moves in quarter hours, from none up to a whole day; an unreported night starts from seven hours. */
const SLEEP_STEP = 0.25;
const MAX_SLEEP = 24;
const DEFAULT_SLEEP = 7;

/** Categories a timed Life event can have, and the message key naming each. */
const EVENT_CATEGORIES = [["sport", "categorySport"], ["social", "categorySocial"], ["chore", "categoryChore"], ["health", "categoryHealth"], ["other", "categoryOther"]];

/** The spoken word for each mark in a habit's week. */
const MARK_KEYS = { done: "habitMarkDone", missed: "habitMarkMissed", unreported: "habitMarkUnreported" };

/**
 * Say how long someone slept.
 * @param {number} hours - Hours of sleep, possibly fractional.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "6 h 20".
 */
function sleepLabel(hours, language) {
  return formatMinutes(Math.round(hours * 60), language);
}

/**
 * Today's check-in: sleep, energy, mood and a note, as the user reports them. Agents may read it but
 * never change it.
 * @param {object} props
 * @param {string} props.date - Today's YYYY-MM-DD date.
 * @param {object|null} props.daily - The check-in already saved, if any.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function CheckInSheet({ date, daily, backendConnected, mutate, onClose }) {
  const { t, language } = useI18n();
  const [sleep, setSleep] = useState(daily?.sleepHours ?? null);
  const [energy, setEnergy] = useState(daily?.energyLevel ? String(daily.energyLevel) : "");
  const [mood, setMood] = useState(daily?.mood ? String(daily.mood) : "");
  const [note, setNote] = useState(daily?.note || "");
  const change = (delta) => setSleep((current) => Math.min(MAX_SLEEP, Math.max(0, (current ?? DEFAULT_SLEEP) + delta)));
  return (
    <SheetForm title={daily ? t("editCheckInTitle") : t("checkInTitle")} submitLabel={t("saveCheckIn")} note={t("checkInPrivacy")}
      backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate(`/api/life/daily/${date}`, "PUT", {
        sleepHours: sleep, energyLevel: energy ? Number(energy) : null, mood: mood ? Number(mood) : null, note: note.trim(),
      })}>
      <div className="dw-field">
        <span className="dw-field-label" id="dw-sleep-label">{t("sleepLabel")}</span>
        <div className="dw-stepper" role="group" aria-labelledby="dw-sleep-label">
          <button type="button" className="dw-button dw-icon-only" aria-label={t("lessSleep")} onClick={() => change(-SLEEP_STEP)}><Icon name="minus" size={18} /></button>
          <output aria-live="polite">{sleep === null ? t("notReportedShort") : sleepLabel(sleep, language)}</output>
          <button type="button" className="dw-button dw-icon-only" aria-label={t("moreSleep")} onClick={() => change(SLEEP_STEP)}><Icon name="plus" size={18} /></button>
        </div>
      </div>
      <div className="dw-field">
        <span className="dw-field-label">{t("energyLabel")}</span>
        <Segmented label={t("energyLabel")} value={energy} onChange={setEnergy} options={ENERGY_LEVELS.map((level) => [level, level])} />
        <span className="dw-caption">{t("energyScale")}</span>
      </div>
      <div className="dw-field">
        <span className="dw-field-label">{t("moodLabel")}</span>
        <Segmented label={t("moodLabel")} value={mood} onChange={setMood} options={MOODS.map((key, index) => [String(index + 1), t(key)])} />
      </div>
      <label className="dw-field"><span>{t("noteLabel")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <textarea maxLength={1000} rows={3} value={note} onChange={(event) => setNote(event.target.value)} /></label>
    </SheetForm>
  );
}

/**
 * A new habit to report on. Reporting is a separate, explicit step each day.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function HabitSheet({ backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [frequency, setFrequency] = useState("daily");
  return (
    <SheetForm title={t("newHabitTitle")} submitLabel={t("saveHabitAction")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/life/habits", "POST", { title: title.trim(), frequency })}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <div className="dw-field"><span className="dw-field-label">{t("fieldRepeats")}</span>
        <Segmented label={t("fieldRepeats")} value={frequency} onChange={setFrequency} options={[["daily", t("flagDaily")], ["weekly", t("flagWeekly")]]} /></div>
    </SheetForm>
  );
}

/**
 * A timed Life event for the day on show. It also appears in Calendar as a task.
 * @param {object} props
 * @param {string} props.date - The event's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function EventSheet({ date, backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [event, setEvent] = useState({ title: "", startTime: "09:00", endTime: "10:00", category: "other", flexible: true });
  const set = (fields) => setEvent((current) => ({ ...current, ...fields }));
  return (
    <SheetForm title={t("newEventTitle")} submitLabel={t("saveEventAction")} note={t("eventCalendarNote")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/life/events", "POST", { date, ...event, title: event.title.trim() })}>
      <label className="dw-field">{t("fieldTitle")}
        <input required pattern=".*\S.*" maxLength={200} value={event.title} onChange={(input) => set({ title: input.target.value })} /></label>
      <div className="dw-field-row">
        <label className="dw-field">{t("fieldStart")}
          <input type="time" required value={event.startTime} onChange={(input) => set({ startTime: input.target.value })} /></label>
        <label className="dw-field">{t("fieldEnd")}
          <input type="time" required value={event.endTime} onChange={(input) => set({ endTime: input.target.value })} /></label>
      </div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldCategory")}</span>
        <Segmented label={t("fieldCategory")} value={event.category} onChange={(category) => set({ category })}
          options={EVENT_CATEGORIES.map(([value, key]) => [value, t(key)])} /></div>
      <label className="dw-switch">
        <input type="checkbox" role="switch" checked={!event.flexible} onChange={(input) => set({ flexible: !input.target.checked })} />
        <span><strong>{t("flagFixed")}</strong><span className="dw-caption">{t("timingFixedHelp")}</span></span>
      </label>
    </SheetForm>
  );
}

/**
 * The day's check-in at a glance, with the note in the user's words.
 * @param {object} props
 * @param {object|null} props.daily - The check-in, if one was saved.
 * @param {boolean} props.isToday - Whether the day on show is today.
 * @param {() => void} props.onEdit - Open the check-in form.
 */
function CheckInCard({ daily, isToday, onEdit }) {
  const { t, language, demoText } = useI18n();
  const tiles = [
    ["sleepLabel", daily?.sleepHours != null ? sleepLabel(daily.sleepHours, language) : "—"],
    ["energyLabel", daily?.energyLevel ? t("energyOf", { level: daily.energyLevel }) : "—"],
    ["moodLabel", daily?.mood ? t(MOODS[daily.mood - 1]) : "—"],
  ];
  return (
    <section className="dw-card" aria-labelledby="dw-checkin-title">
      <h2 id="dw-checkin-title" className="dw-heading dw-card-title">{t("checkInCardTitle")}</h2>
      {daily ? (
        <>
          <ul className="dw-day-tallies dw-checkin-tiles">
            {tiles.map(([key, value]) => <li key={key}><span>{t(key)}</span><strong>{value}</strong></li>)}
          </ul>
          {daily.note && <p className="dw-muted">“{demoText(daily.note)}”</p>}
        </>
      ) : <p className="dw-muted">{t("noCheckIn")}</p>}
      {isToday && <button type="button" className="dw-button dw-button-quiet" onClick={onEdit}><Icon name="pencil" size={18} />{daily ? t("editCheckInAction") : t("checkInAction")}</button>}
    </section>
  );
}

/**
 * Each habit's week, as reported: done, missed, or not reported. Nothing is filled in for the user.
 * @param {object} props
 * @param {object} props.data - The Life snapshot.
 * @param {boolean} props.isToday - Whether today's outcome can be reported.
 * @param {boolean} props.canPrepare - Whether habits can be added, paused or resumed.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => void} props.act - Save a change from the page.
 * @param {() => void} props.onNewHabit - Open the new habit form.
 */
function HabitsCard({ data, isToday, canPrepare, backendConnected, act, onNewHabit }) {
  const { t, language, demoText } = useI18n();
  const week = Array.from({ length: 7 }, (_, index) => addDays(data.weekStart, index));
  const logOf = (habitId, date) => data.weekLogs.find((log) => log.habitId === habitId && log.date === date);
  const markOf = (habitId, date) => {
    const log = logOf(habitId, date);
    if (log) return log.done ? "done" : "missed";
    return date <= data.date ? "unreported" : "ahead";
  };
  const narrow = new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "narrow" });
  return (
    <section className="dw-card" aria-labelledby="dw-habits-title">
      <div className="dw-card-head">
        <h2 id="dw-habits-title" className="dw-heading">{t("habitsTitle")}</h2>
        <span className="dw-caption">{t("habitsWeekNote")}</span>
      </div>
      {data.habits.length ? (
        <ul className="dw-habits">
          {data.habits.map((habit) => {
            const title = demoText(habit.title);
            const marks = week.map((date) => [date, markOf(habit.id, date)]);
            const todayLog = logOf(habit.id, data.date);
            const summary = marks.filter(([, mark]) => mark !== "ahead")
              .map(([date, mark]) => `${longDate(date, language).weekday} ${t(MARK_KEYS[mark])}`).join(t("clauseSeparator"));
            return (
              <li key={habit.id} className={habit.active ? undefined : "dw-habit-paused"}>
                <p className="dw-habit-head"><strong>{title}</strong>
                  <span className="dw-caption">{habit.active ? t("reportedThisWeek", { count: marks.filter(([, mark]) => mark === "done" || mark === "missed").length }) : t("pausedLabel")}</span></p>
                <ol className="dw-habit-week" aria-label={`${title}: ${summary}`}>
                  {marks.map(([date, mark]) => (
                    <li key={date} aria-hidden="true"><span className="dw-caption">{narrow.format(new Date(`${date}T12:00:00`))}</span>
                      <span className={`dw-habit-mark dw-habit-${mark}`}>{mark === "done" && <Icon name="check" size={12} />}{mark === "missed" && <Icon name="x" size={12} />}</span></li>
                  ))}
                </ol>
                <div className="dw-actions">
                  {isToday && habit.active && (
                    <>
                      <button type="button" className="dw-button" aria-pressed={todayLog?.done === 1} disabled={!backendConnected}
                        onClick={() => act(`/api/life/habits/${habit.id}/logs/${data.date}`, "PUT", { done: true, note: "" })}><Icon name="check" size={18} />{t("habitDoneAction")}</button>
                      <button type="button" className="dw-button" aria-pressed={todayLog?.done === 0} disabled={!backendConnected}
                        onClick={() => act(`/api/life/habits/${habit.id}/logs/${data.date}`, "PUT", { done: false, note: "" })}><Icon name="x" size={18} />{t("habitMissedAction")}</button>
                    </>
                  )}
                  {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
                    onClick={() => act(`/api/life/habits/${habit.id}`, "PATCH", { active: !habit.active })}>{habit.active ? t("pauseAction") : t("resumeAction")}</button>}
                </div>
              </li>
            );
          })}
        </ul>
      ) : <p className="dw-muted">{t("noHabitsYet")}</p>}
      <p className="dw-habit-legend" aria-hidden="true">
        <span><span className="dw-habit-mark dw-habit-done"><Icon name="check" size={12} /></span>{t("habitMarkDone")}</span>
        <span><span className="dw-habit-mark dw-habit-missed"><Icon name="x" size={12} /></span>{t("habitMarkMissed")}</span>
        <span><span className="dw-habit-mark dw-habit-unreported" />{t("habitMarkUnreported")}</span>
      </p>
      {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={onNewHabit}><Icon name="plus" size={18} />{t("newHabitAction")}</button>}
    </section>
  );
}

/**
 * The day's timed Life events, which also stand in Calendar as tasks.
 * @param {object} props
 * @param {object[]} props.events - The day's events.
 * @param {boolean} props.canPrepare - Whether events can be added.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onAdd - Open the new event form.
 */
function EventsCard({ events, canPrepare, backendConnected, onAdd }) {
  const { t, demoText } = useI18n();
  const category = (value) => t(EVENT_CATEGORIES.find(([key]) => key === value)?.[1] || "categoryOther");
  return (
    <section className="dw-card" aria-labelledby="dw-events-title">
      <div className="dw-card-head">
        <h2 id="dw-events-title" className="dw-heading">{t("eventsTitle")}</h2>
        {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={onAdd}><Icon name="plus" size={18} />{t("addAction")}</button>}
      </div>
      {events.length ? (
        <ul className="dw-day-rows">
          {events.map((event) => (
            <li key={event.id} className="dw-day-row">
              <span className="dw-plan-time">{event.startTime}</span>
              <span className="dw-day-row-title">{demoText(event.title)}<span className="dw-caption">{category(event.category)}</span></span>
              {event.constraintKind === "fixed" ? <span className="dw-row-flags"><span><Icon name="pin" size={16} />{t("flagFixed")}</span></span> : <span />}
            </li>
          ))}
        </ul>
      ) : <p className="dw-muted">{t("noEventsYet")}</p>}
    </section>
  );
}

/**
 * Life & Rest's own records: check-in, habits and timed events, shown by tab.
 * @param {object} props
 * @param {string} props.tab - The tab on show.
 * @param {object} props.data - The Life snapshot for the day on show.
 * @param {boolean} props.isToday - Whether the day on show is today.
 * @param {boolean} props.canPrepare - Whether catalogues can change for the day on show.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change from a form.
 * @param {(path: string, method: string, body: object) => void} props.act - Save a change from the page.
 * @param {string|null} props.sheet - The form open, if any.
 * @param {(sheet: string|null) => void} props.setSheet - Open or close a form.
 */
export function LifeArea({ tab, data, isToday, canPrepare, backendConnected, mutate, act, sheet, setSheet }) {
  const show = (id) => tab === "overview" || tab === id;
  const close = () => setSheet(null);
  return (
    <>
      {show("checkin") && <CheckInCard daily={data.daily} isToday={isToday} onEdit={() => setSheet("checkin")} />}
      {show("habits") && <HabitsCard data={data} isToday={isToday} canPrepare={canPrepare} backendConnected={backendConnected} act={act} onNewHabit={() => setSheet("habit")} />}
      {show("events") && <EventsCard events={data.events} canPrepare={canPrepare} backendConnected={backendConnected} onAdd={() => setSheet("event")} />}
      {sheet === "checkin" && <CheckInSheet date={data.date} daily={data.daily} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
      {sheet === "habit" && <HabitSheet backendConnected={backendConnected} mutate={mutate} onClose={close} />}
      {sheet === "event" && <EventSheet date={data.date} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
    </>
  );
}
