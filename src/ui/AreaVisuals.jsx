import { useI18n } from "../i18n";
import { shortDate } from "../time";
import { areaOf } from "./AreaTag";
import { barMarks, dayDots, habitSquares, practiceDots, stepSegments, weekdayLetters } from "./visuals";

/** The words each habit day's state reads as, by message key. */
const HABIT_DAY_TEXT = { done: "habitDayDone", partial: "habitDayPartial", missed: "habitDayMissed",
  upcoming: "habitDayUpcoming", off: "habitDayOff" };
/** The words each practice day's state reads as, by message key. */
const PRACTICE_DAY_TEXT = { practised: "practiceDayPractised", planned: "practiceDayPlanned", none: "practiceDayNone" };

/**
 * A week of bars, one per day with its value printed above it and its weekday under it; the part
 * done is darker inside each bar, and a guide line can mark a level.
 * @param {object} props
 * @param {{date: string, value: number|null, done?: number}[]} props.days - Each day's value and the part done.
 * @param {string} props.area - The area whose colours the bars take, as AreaTag names it.
 * @param {string} props.label - The row's accessible name.
 * @param {(bar: object) => string} props.dayLabel - A bar's accessible name, with its numbers.
 * @param {(bar: object) => string} props.valueText - The value printed above a bar.
 * @param {{max?: number, guide?: number, low?: number}} [props.scale] - As barMarks takes it.
 * @param {string} [props.current] - The day to mark as the one on show.
 */
export function LoadBars({ days, area, label, dayLabel, valueText, scale, current }) {
  const { language } = useI18n();
  const { bars, guideAt } = barMarks(days, scale);
  const letters = weekdayLetters(days.map((day) => day.date), language);
  return (
    <ol className={`dw-load-bars dw-area-${area}`} aria-label={label}>
      {bars.map((bar, index) => (
        <li key={bar.date} className={bar.date === current ? "dw-load-today" : undefined} aria-label={dayLabel(bar)}>
          <span className="dw-caption dw-load-value" aria-hidden="true">{valueText(bar)}</span>
          <span className="dw-load-bar" aria-hidden="true">
            {guideAt != null && <span className="dw-load-guide" style={{ bottom: `${guideAt}%` }} />}
            <span className={`dw-load-planned${bar.low ? " dw-load-low" : ""}`} style={{ height: `${bar.height}%` }}>
              {bar.doneHeight > 0 && <span className="dw-load-done" style={{ height: `${(bar.doneHeight / bar.height) * 100}%` }} />}
            </span>
          </span>
          <span className="dw-caption" aria-hidden="true">{letters[index]}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * A habit's week, a square per day from Monday to Sunday: filled when done, light when partly done,
 * outlined with ✗ when missed, dashed while still to come, and empty when its rule skips the day.
 * @param {object} props
 * @param {string[]} props.days - Each day's state, as Life's overview lists it.
 * @param {string[]} props.dates - The week's days, YYYY-MM-DD.
 * @param {string} props.label - The grid's accessible name.
 */
export function HabitWeek({ days, dates, label }) {
  const { t, language } = useI18n();
  const letters = weekdayLetters(dates, language);
  return (
    <ol className={`dw-habit-week dw-area-${areaOf("life")}`} aria-label={label}>
      {habitSquares(days).map((square, index) => (
        <li key={dates[index]}>
          <span className={`dw-habit-day dw-habit-${square.state}`} role="img"
            aria-label={`${shortDate(dates[index], language)}: ${t(HABIT_DAY_TEXT[square.state])}`}>{square.symbol}</span>
          <span className="dw-caption" aria-hidden="true">{letters[index]}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * A subject's practice through the week: ● practised, ○ planned but not done, · nothing planned.
 * @param {object} props
 * @param {string[]} props.days - Each day's state, as Learning's overview lists it.
 * @param {string[]} props.dates - The week's days, YYYY-MM-DD.
 * @param {string} props.label - The row's accessible name.
 */
export function PracticeDots({ days, dates, label }) {
  const { t, language } = useI18n();
  const letters = weekdayLetters(dates, language);
  return (
    <ol className={`dw-practice-dots dw-area-${areaOf("learning")}`} aria-label={label}>
      {practiceDots(days).map((dot, index) => (
        <li key={dates[index]} aria-label={`${shortDate(dates[index], language)}: ${t(PRACTICE_DAY_TEXT[dot.state])}`}>
          <span className={`dw-practice-dot dw-practice-${dot.state}`} aria-hidden="true">{dot.symbol}</span>
          <span className="dw-caption" aria-hidden="true">{letters[index]}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * A project's steps as one bar, a segment per step in order, filled once done or partly done.
 * @param {object} props
 * @param {{id: string, title: string, status: string}[]} props.steps - The project's tasks.
 * @param {string} props.label - The bar's accessible name, with its count.
 */
export function StepBar({ steps, label }) {
  const { demoText } = useI18n();
  return (
    <span className={`dw-step-bar dw-area-${areaOf("project")}`} role="img" aria-label={label}>
      {stepSegments(steps).map((segment) => (
        <span key={segment.id} className={segment.filled ? "dw-step-done" : undefined} title={demoText(segment.title)} />
      ))}
    </span>
  );
}

/**
 * Seven days as dots, each bigger for more items on it, with its count inside and its weekday under it.
 * @param {object} props
 * @param {string[]} props.dates - The days, YYYY-MM-DD.
 * @param {{date: string}[]} props.items - The items listed under the row, each on its day.
 * @param {string} props.label - The row's accessible name.
 * @param {string} props.area - The area whose colours the dots take, as AreaTag names it.
 */
export function DayDots({ dates, items, label, area }) {
  const { t, language } = useI18n();
  const letters = weekdayLetters(dates, language);
  return (
    <ol className={`dw-day-dots dw-area-${area}`} aria-label={label}>
      {dayDots(dates, items).map((dot, index) => (
        <li key={dot.date} aria-label={t("dayDotsLabel", { day: shortDate(dot.date, language), count: dot.count })}>
          <span className={`dw-day-dot dw-day-dot-${dot.size}`} aria-hidden="true">{dot.count || ""}</span>
          <span className="dw-caption" aria-hidden="true">{letters[index]}</span>
        </li>
      ))}
    </ol>
  );
}
