import { Fragment } from "react";
import { useI18n } from "../i18n";
import { shortDate } from "../time";
import { areaOf } from "./AreaTag";
import { ENERGY_LEVELS, ENERGY_LOW, barMarks, dayDots, energyBars, energyMeter, energySteps, habitSquares, practiceDots,
  stepSegments, weekdayLetters } from "./visuals";

/** The words each habit day's state reads as, by message key. */
const HABIT_DAY_TEXT = { done: "habitDayDone", partial: "habitDayPartial", missed: "habitDayMissed",
  upcoming: "habitDayUpcoming", off: "habitDayOff" };
/** The words each practice day's state reads as, by message key. */
const PRACTICE_DAY_TEXT = { practised: "practiceDayPractised", planned: "practiceDayPlanned", none: "practiceDayNone" };

/**
 * A week of bars, one per day with its value printed above it and its weekday under it; the part
 * done is darker inside each bar.
 * @param {object} props
 * @param {{date: string, value: number|null, done?: number}[]} props.days - Each day's value and the part done.
 * @param {string} props.area - The area whose colours the bars take, as AreaTag names it.
 * @param {string} props.label - The row's accessible name.
 * @param {(bar: object) => string} props.dayLabel - A bar's accessible name, with its numbers.
 * @param {(bar: object) => string} props.valueText - The value printed above a bar.
 * @param {string} [props.current] - The day to mark as the one on show.
 */
export function LoadBars({ days, area, label, dayLabel, valueText, current }) {
  const { language } = useI18n();
  const letters = weekdayLetters(days.map((day) => day.date), language);
  return (
    <ol className={`dw-load-bars dw-area-${area}`} aria-label={label}>
      {barMarks(days).map((bar, index) => (
        <li key={bar.date} className={bar.date === current ? "dw-load-today" : undefined} aria-label={dayLabel(bar)}>
          <span className="dw-caption dw-load-value" aria-hidden="true">{valueText(bar)}</span>
          <span className="dw-load-bar" aria-hidden="true">
            <span className="dw-load-planned" style={{ height: `${bar.height}%` }}>
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
 * A project's steps as one bar, a segment per step in order, filled once fully done.
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

/**
 * A day's energy as steps across 09:00–22:00, each reading's level, from 1 at the bottom to 5 at the
 * top, held until the next; a dot marks each reading, low ones in the caution colour, and the
 * readings with their times and the day's average are in words beneath.
 * @param {object} props
 * @param {{level: number, time: string}[]} props.readings - The day's readings in order.
 * @param {string} props.until - The "HH:MM" the last reading holds to: now on today, 22:00 on another day.
 * @param {number|null} props.average - The day's average.
 */
export function EnergySteps({ readings, until, average }) {
  const { t } = useI18n();
  const listed = readings.map((reading) => `${reading.time} · ${reading.level}`).join(t("listSeparator"));
  return (
    <figure className="dw-energy-steps-figure">
      <div className="dw-energy-plot">
        <span className="dw-caption dw-energy-axis" aria-hidden="true"><span>5</span><span>1</span></span>
        <div className="dw-energy-steps" role="img" aria-label={t("energyStepsLabel", { readings: listed, average })}>
          {[0, 25, 50, 75, 100].map((level) => <span key={level} className="dw-energy-level" style={{ bottom: `${level}%` }} />)}
          {energySteps(readings, until).map((step, index) => (
            <Fragment key={`${step.time}-${index}`}>
              {step.rise && <span className="dw-energy-rise" style={{ left: `${step.left}%`, bottom: `${step.rise.bottom}%`, height: `${step.rise.height}%` }} />}
              <span className="dw-energy-step" style={{ left: `${step.left}%`, bottom: `${step.bottom}%`, width: `${step.width}%` }} />
              <span className={`dw-energy-dot${step.low ? " dw-energy-dot-low" : ""}`} style={{ left: `${step.left}%`, bottom: `${step.bottom}%` }} />
            </Fragment>
          ))}
        </div>
        <span className="dw-caption dw-energy-hours" aria-hidden="true"><span>09:00</span><span>22:00</span></span>
      </div>
      <figcaption className="dw-caption">{t("energyReadingsLine", { readings: listed, average })}</figcaption>
    </figure>
  );
}

/**
 * Days' energy as bars, one per day: its average out of 5, low ones in the caution colour, with a
 * thin line from its lowest to its highest reading where they differ, and a dashed guide at ENERGY_LOW. A week prints
 * each average above its bar and its weekday under it; a month, too narrow for that, its date under
 * it; each bar says its numbers to a screen reader.
 * @param {object} props
 * @param {{date: string, average: number|null, low: number|null, high: number|null}[]} props.days - Each day, in order.
 * @param {string} props.label - The row's accessible name.
 * @param {string} [props.current] - The day to mark as the one on show.
 */
export function EnergyBars({ days, label, current }) {
  const { t, language } = useI18n();
  const month = days.length > 7;
  const letters = weekdayLetters(days.map((day) => day.date), language);
  return (
    <ol className={`dw-energy-bars${month ? " dw-energy-bars-month" : ""}`} aria-label={label}>
      {energyBars(days).map((bar, index) => (
        <li key={bar.date} className={bar.date === current ? "dw-load-today" : undefined}
          aria-label={bar.empty ? t("barReading", { day: shortDate(bar.date, language), level: t("notReportedShort") })
            : t("energyDayBar", { day: shortDate(bar.date, language), average: bar.average, low: bar.lowest, high: bar.highest })}>
          {!month && <span className="dw-caption dw-load-value" aria-hidden="true">{bar.average ?? t("energyNoReading")}</span>}
          <span className="dw-energy-bar" aria-hidden="true">
            <span className="dw-load-guide" style={{ bottom: `${(ENERGY_LOW / ENERGY_LEVELS) * 100}%` }} />
            {!bar.empty && <span className={`dw-energy-fill${bar.low ? " dw-energy-fill-low" : ""}`} style={{ height: `${bar.height}%` }} />}
            {bar.rangeHeight > 0 && <span className="dw-energy-range" style={{ bottom: `${bar.rangeBottom}%`, height: `${bar.rangeHeight}%` }} />}
          </span>
          <span className="dw-caption" aria-hidden="true">{month ? Number(bar.date.slice(-2)) : letters[index]}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * A meter of five steps for a day's average energy, as many filled as it rounds to, in the caution
 * colour at ENERGY_LOW or below; outlined and empty when nothing was reported. It shows no text: a
 * meter with a label says it to a screen reader, and one without is hidden, as its Calendar cell names it.
 * @param {object} props
 * @param {number|null} props.average - The day's average, or null.
 * @param {boolean} [props.large=false] - The day panel's larger meter.
 * @param {string} [props.label] - Its accessible name.
 */
export function EnergyMeter({ average, large = false, label }) {
  const meter = energyMeter(average);
  return (
    <span className={`dw-energy-meter${large ? " dw-energy-meter-large" : ""}${meter.caution ? " dw-energy-meter-caution" : ""}${meter.empty ? " dw-energy-meter-empty" : ""}`}
      role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : "true"}>
      {meter.steps.map((on, index) => <span key={index} className={`dw-meter-step${on ? " dw-meter-on" : ""}`} />)}
    </span>
  );
}
