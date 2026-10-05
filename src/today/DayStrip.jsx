import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { areaOf } from "../ui/AreaTag";
import { clockOf, formatMinutes, timeRange } from "../time";
import { DAY_START_MINUTES, dayStrip, hourMarks } from "./stripLayout";

/**
 * How far to pull a label back over its point, as a percentage of its own width: none at the
 * strip's start, all of it at the end, and half in between, so a label never runs off the strip.
 * @param {number} at - Where the label's point falls, as a percentage of the strip's width.
 * @returns {number} The percentage to shift the label left by.
 */
const labelShift = (at) => (at <= 0 ? 0 : at >= 100 ? 100 : 50);

/** Where the now mark sits when none is drawn, far enough off the strip that no hour gives way to it. */
const NO_NOW = -100;

/**
 * The day at a glance in Today's header, shown even before anything is recorded: its timed tasks in
 * their area colours across 09:00–22:00, lunch and dinner kept free, a mark at the time now with
 * that time printed under it and the time already gone shaded, what comes next, how much of the day
 * is left, and a key that splits it into meals, tasks and open time. The schedule below holds the
 * detail; each block names its task when pointed at.
 *
 * An area's screen draws it two more ways: with `area`, one area's tasks alone, without the caption
 * or the key; with `whole`, the whole day, with the key counting from 09:00 and no now mark.
 * @param {object} props
 * @param {object[]} props.timed - The day's timed rows, from dayRows.
 * @param {object|null} [props.next] - The next task still to do, from TodayScreen.
 * @param {number} props.now - Minutes after midnight now.
 * @param {boolean} [props.empty=false] - Nothing is recorded for the day yet.
 * @param {object[]} props.dayMeals - The day's lunch and dinner, as the local service lists them.
 * @param {string|null} [props.area=null] - Draw only this area's tasks.
 * @param {boolean} [props.whole=false] - Draw the whole day, with its key over all of it.
 * @param {boolean} [props.showNow=true] - Mark the time now and shade the time gone, as for today.
 * @param {string} [props.label] - The strip's accessible name, when not Today's own.
 */
export function DayStrip({ timed, next = null, now, dayMeals, empty = false, area = null, whole = false, showNow = true, label }) {
  const { t, language, demoText } = useI18n();
  const marking = showNow && !whole;
  const { tasks, meals, nowAt, leftMinutes, mealMinutes, taskMinutes, openMinutes } =
    dayStrip(timed, whole ? DAY_START_MINUTES : now, dayMeals, { area });
  const open = formatMinutes(openMinutes, language);
  const compact = Boolean(area) || whole;
  return (
    <section className={`dw-daystrip${compact ? " dw-daystrip-compact" : ""}`} aria-label={label || t("dayStripLabel")}>
      {!compact && (
        <p className="dw-daystrip-caption">
          {next
            ? <span className="dw-daystrip-next"><strong>{t("dayStripNext")}</strong><span>{demoText(next.title)}</span>
              <span className="dw-daystrip-when">{next.start_time || t("dayStripUntimed")}</span></span>
            : <span>{t(empty ? "dayStripNoTasks" : "dayStripNoNext")}</span>}
          <span className="dw-daystrip-open">{leftMinutes > 0
            ? t("dayStripLeft", { time: clockOf(now), left: formatMinutes(leftMinutes, language) })
            : t("dayStripDayOver", { time: clockOf(now) })}</span>
        </p>
      )}
      <div className="dw-daystrip-lane">
        <div className="dw-daystrip-track" role="img" aria-label={t(tasks.length === 1 ? "dayStripSummaryOne" : "dayStripSummary", { count: tasks.length, open })}>
          {meals.map((meal) => (
            <span key={meal.title} className="dw-daystrip-meal" style={{ left: `${meal.left}%`, width: `${meal.width}%` }}
              title={demoText(meal.title)}><Icon name="meal" size={12} /></span>
          ))}
          {tasks.map(({ row, paused, left, width }) => (
            <span key={`${row.kind}-${row.id}`} style={{ left: `${left}%`, width: `${width}%` }}
              className={`dw-daystrip-task dw-area-${areaOf(row.domain) || "none"} dw-daystrip-${paused ? "paused" : row.completion_status}`}
              title={`${timeRange(row.start_time, row.duration_minutes)} ${demoText(row.title)} · ${t(paused ? "paused" : row.completion_status)}`} />
          ))}
          {marking && <span className="dw-daystrip-past" style={{ width: `${nowAt}%` }} />}
        </div>
        {marking && <span className="dw-daystrip-now" style={{ left: `${nowAt}%` }} />}

      </div>
      <div className="dw-daystrip-hours" aria-hidden="true">
        {hourMarks(marking ? nowAt : NO_NOW).map(({ clock, at }) => (
          <span key={clock} style={{ left: `${at}%`, transform: `translateX(-${labelShift(at)}%)` }}>{clock}</span>
        ))}
        {/* Pulled back by as much of its width as the mark is along the strip, so it stays on it at any time. */}
        {marking && <span className="dw-daystrip-now-time" style={{ left: `${nowAt}%`, transform: `translateX(-${nowAt}%)` }}>{clockOf(now)}</span>}
      </div>
      {/* What the time left holds, so the hatched blocks read as lunch and dinner, kept free. */}
      {(whole || (!compact && leftMinutes > 0)) && (
        <ul className="dw-daystrip-key" aria-label={t(whole ? "dayStripWholeKey" : "dayStripKey")}>
          <li><span className="dw-daystrip-swatch dw-daystrip-meal" />{t("dayStripMeals", { minutes: formatMinutes(mealMinutes, language) })}</li>
          <li><span className="dw-daystrip-swatch dw-daystrip-swatch-task" />{t(whole ? "dayStripBooked" : "dayStripTasks", { minutes: formatMinutes(taskMinutes, language) })}</li>
          <li><span className="dw-daystrip-swatch dw-daystrip-swatch-open" />{t("dayStripOpen", { minutes: open })}</li>
        </ul>
      )}
    </section>
  );
}
