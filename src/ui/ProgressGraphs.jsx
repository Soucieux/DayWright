import { useI18n } from "../i18n";
import { barTime } from "../records/areaOverview";
import { formatMinutes, shortDate } from "../time";
import { AreaGlyph, DOMAINS, areaOf } from "./AreaTag";
import { FOLLOW_PARTS, areaDayBars, finishingBars, finishingTotals, followThroughParts, followThroughTotals, goalBurnup,
  padDays } from "./progress";
import { weekdayLetters } from "./visuals";

/** Each follow-through part's words, by message key. */
const FOLLOW_TEXT = { done: "done", partial: "partial", moved: "followMoved", skipped: "skipped", noReply: "noReply",
  unreported: "followNotYet" };
/** A burn-up names every week under its column up to this many weeks; beyond, only the first, this and the last. */
const BURNUP_NAMED_WEEKS = 8;

/**
 * The caption under each day's bar: its weekday letter in a week, its day of the month in a month.
 * @param {string[]} dates - The days, YYYY-MM-DD.
 * @param {string} language - `en` or `zh`.
 * @returns {string[]} Each day's caption.
 */
function dayCaptions(dates, language) {
  return dates.length > 7 ? dates.map((date) => String(Number(date.slice(-2)))) : weekdayLetters(dates, language);
}

/**
 * A follow-through's parts in words, such as "Done 4, Skipped 1".
 * @param {object} counts - The entries in each part.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} The parts that have any, each with its count.
 */
function followWords(counts, t) {
  return FOLLOW_PARTS.filter((key) => counts[key]).map((key) => `${t(FOLLOW_TEXT[key])} ${counts[key]}`).join(t("listSeparator"));
}

/**
 * A period's planned time fully done, a bar per day stacked by area, its time above it in a week,
 * then the period's total and each area's. With nothing fully done, a line says so.
 * @param {object} props
 * @param {string} props.start - The period's first day, YYYY-MM-DD.
 * @param {string} props.end - Its last day.
 * @param {{date: string, minutes: object}[]} props.days - The days the service counted, none after today.
 */
export function DoneByArea({ start, end, days }) {
  const { t, language } = useI18n();
  const padded = padDays(start, end, days);
  const bars = areaDayBars(padded, DOMAINS);
  const total = bars.reduce((sum, bar) => sum + bar.total, 0);
  if (!total) return <p className="dw-muted">{t("doneByAreaEmpty")}</p>;
  const month = padded.length > 7;
  const captions = dayCaptions(padded.map((day) => day.date), language);
  const byArea = DOMAINS.map((domain) => [domain, padded.reduce((sum, day) => sum + (day.minutes[domain] || 0), 0)])
    .filter(([, minutes]) => minutes);
  return (
    <>
      <ol className={`dw-graph-bars${month ? " dw-graph-bars-month" : ""}`} aria-label={t("doneByAreaLabel")}>
        {bars.map((bar, index) => (
          <li key={bar.date} aria-label={bar.empty ? t("doneByAreaNone", { day: shortDate(bar.date, language) })
            : t("doneByAreaDay", { day: shortDate(bar.date, language), total: formatMinutes(bar.total, language),
              areas: bar.parts.map((part) => `${t(part.domain)} ${formatMinutes(part.minutes, language)}`).join(t("listSeparator")) })}>
            {!month && <span className="dw-caption dw-load-value" aria-hidden="true">{barTime(bar.total)}</span>}
            <span className="dw-graph-bar" aria-hidden="true">
              {bar.parts.map((part) => (
                <span key={part.domain} className={`dw-graph-part dw-area-${areaOf(part.domain)}`} style={{ height: `${part.height}%` }} />
              ))}
            </span>
            <span className="dw-caption" aria-hidden="true">{captions[index]}</span>
          </li>
        ))}
      </ol>
      <ul className="dw-report-list dw-graph-figures">
        <li>{t("doneByAreaTotal", { total: formatMinutes(total, language), days: bars.filter((bar) => !bar.empty).length })}</li>
        <li className="dw-graph-key">{byArea.map(([domain, minutes]) => (
          <span key={domain}><AreaGlyph domain={domain} />{t(domain)} {formatMinutes(minutes, language)}</span>
        ))}</li>
      </ul>
    </>
  );
}

/**
 * Each day's share of its tasks fully done, a bar per day with its percentage above it in a week,
 * then the period's total. Until FINISHING_MIN_DAYS days have tasks, a line says so instead.
 * @param {object} props
 * @param {{date: string, scheduled: number, done: number}[]} props.days - Every day of the span, in order.
 * @param {boolean} [props.mini] - Draw the small version, with no percentages above the bars.
 */
export function FinishingBars({ days, mini = false }) {
  const { t, language } = useI18n();
  const totals = finishingTotals(days);
  if (!totals.enough) return <p className="dw-muted">{t("finishingTooFew")}</p>;
  const month = days.length > 7;
  const captions = dayCaptions(days.map((day) => day.date), language);
  return (
    <>
      <ol className={`dw-graph-bars${month ? " dw-graph-bars-month" : ""}${mini ? " dw-graph-bars-mini" : ""}`} aria-label={t("finishingLabel")}>
        {finishingBars(days).map((bar, index) => (
          <li key={bar.date} aria-label={bar.empty ? t("finishingDayNone", { day: shortDate(bar.date, language) })
            : t("finishingDay", { day: shortDate(bar.date, language), done: bar.done, scheduled: bar.scheduled, rate: bar.rate })}>
            {!month && !mini && <span className="dw-caption dw-load-value" aria-hidden="true">{bar.empty ? "–" : `${bar.rate}%`}</span>}
            <span className="dw-graph-bar" aria-hidden="true">
              {!bar.empty && <span className="dw-graph-fill" style={{ height: `${bar.height}%` }} />}
            </span>
            <span className="dw-caption" aria-hidden="true">{captions[index]}</span>
          </li>
        ))}
      </ol>
      <p className="dw-caption dw-graph-total">{t("finishingTotal", totals)}</p>
    </>
  );
}

/**
 * A key to a follow-through, on one line that wraps: every part with the swatch it is drawn with,
 * its count and its name.
 * @param {object} props
 * @param {object} props.counts - The entries in each part.
 */
function FollowKey({ counts }) {
  const { t } = useI18n();
  return (
    <ul className="dw-follow-key">
      {FOLLOW_PARTS.map((key) => (
        <li key={key}><span className={`dw-follow-swatch dw-follow-${key}`} aria-hidden="true" /><strong>{counts[key]}</strong>
          {t(FOLLOW_TEXT[key])}</li>
      ))}
    </ul>
  );
}

/**
 * How one day's set plan was followed: a bar of its entries, done at the left, then partly done,
 * moved on to another day, skipped and not reported, and a key with each part's count.
 * @param {object} props
 * @param {{done: number, partial: number, moved: number, skipped: number, noReply: number, unreported: number}} props.counts - Its entries in each part.
 */
export function FollowThroughBar({ counts }) {
  const { t } = useI18n();
  const { total, parts } = followThroughParts(counts);
  return (
    <div className="dw-follow">
      <div className="dw-follow-bar" role="img" aria-label={t("followBarLabel", { parts: followWords(counts, t), total })}>
        {parts.map((part) => <span key={part.key} className={`dw-follow-part dw-follow-${part.key}`} style={{ width: `${part.share}%` }} />)}
      </div>
      <FollowKey counts={counts} />
    </div>
  );
}

/**
 * How a period's set plans were followed: a column per day, its entries stacked as one day's bar
 * stacks them, empty on a day with no set plan; then the totals and the key. With no set plan in
 * the period, a line says so.
 * @param {object} props
 * @param {string} props.start - The period's first day, YYYY-MM-DD.
 * @param {string} props.end - Its last day.
 * @param {object[]} props.days - Each day with a set plan, with its entries in each part.
 */
export function FollowThroughDays({ start, end, days }) {
  const { t, language } = useI18n();
  if (!days.length) return <p className="dw-muted">{t("followEmpty")}</p>;
  const known = new Map(days.map((day) => [day.date, day]));
  const dates = padDays(start, end, []).map((day) => day.date);
  const captions = dayCaptions(dates, language);
  const totals = followThroughTotals(days);
  return (
    <>
      <ol className={`dw-graph-bars${dates.length > 7 ? " dw-graph-bars-month" : ""}`} aria-label={t("followLabel")}>
        {dates.map((date, index) => {
          const day = known.get(date);
          const parts = day ? followThroughParts(day).parts : [];
          return (
            <li key={date} aria-label={day ? t("followDayBar", { day: shortDate(date, language), parts: followWords(day, t) })
              : t("followDayNone", { day: shortDate(date, language) })}>
              <span className="dw-graph-bar" aria-hidden="true">
                {parts.map((part) => <span key={part.key} className={`dw-follow-part dw-follow-${part.key}`} style={{ height: `${part.share}%` }} />)}
              </span>
              <span className="dw-caption" aria-hidden="true">{captions[index]}</span>
            </li>
          );
        })}
      </ol>
      <p className="dw-caption dw-graph-total">{t("followTotal", { total: FOLLOW_PARTS.reduce((sum, key) => sum + totals[key], 0), days: totals.days })}</p>
      <FollowKey counts={totals} />
    </>
  );
}

/**
 * Today's finishing over the last seven days, small, in its own card in Day details: the bars,
 * today's tasks fully done, and the seven days' total.
 * @param {object} props
 * @param {{date: string, scheduled: number, done: number}[]} props.days - The days to the day on show.
 * @param {string} props.date - The day on show.
 */
export function FinishingCard({ days, date }) {
  const { t } = useI18n();
  const shown = days.find((day) => day.date === date);
  return (
    <section className="dw-card" aria-labelledby="dw-finishing-title">
      <div className="dw-card-head"><h2 id="dw-finishing-title" className="dw-heading">{t("finishingCardTitle")}</h2>
        <span className="dw-caption">{t("finishingCardCaption")}</span></div>
      <FinishingBars days={days} mini />
      {shown?.scheduled > 0 && <p className="dw-caption">{t("finishingToday", shown)}</p>}
    </section>
  );
}

/**
 * A goal's progress by week, as a burn-up: a column a week of its steps fully done so far, this week
 * and the weeks ahead outlined to the steps planned through them, under a dashed line at all its
 * steps; then the figures in words and a key. With no steps yet, a line says so.
 * @param {object} props
 * @param {{startAt: string, linkedItems: {date: string, status: string}[]}} props.goal - The goal and its tasks.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 */
export function GoalBurnup({ goal, today }) {
  const { t, language } = useI18n();
  const burnup = goalBurnup(goal.linkedItems.map(({ date, status }) => ({ date, status })), goal.startAt, today);
  if (!burnup.total) return <p className="dw-muted">{t("goalProgressEmpty")}</p>;
  const share = (count) => `${(count / burnup.total) * 100}%`;
  const named = (index, week) => burnup.weeks.length <= BURNUP_NAMED_WEEKS || !index || week.current || index === burnup.weeks.length - 1;
  const weekDay = (start) => new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { day: "numeric", month: "short" })
    .format(new Date(`${start}T12:00:00`));
  // A week ahead names the steps planned by then; this week, its steps done and, when more are planned, those too.
  const weekName = (week) => {
    const values = { day: shortDate(week.start, language), done: week.done, planned: week.planned, total: burnup.total };
    if (week.future) return t("goalProgressAhead", values);
    return week.planned > week.done ? t("goalProgressCurrent", values) : t("goalProgressWeek", values);
  };
  return (
    <figure className={`dw-burnup-figure dw-area-${areaOf(goal.domain)}`}>
      <ol className="dw-burnup" aria-label={t("goalProgressLabel", { total: burnup.total })}>
        {burnup.weeks.map((week, index) => (
          <li key={week.start} className={week.current ? "dw-load-today" : undefined}
            aria-label={weekName(week)}>
            <span className="dw-burnup-bar" aria-hidden="true">
              {week.planned > (week.done ?? 0) && <span className="dw-burnup-planned" style={{ height: share(week.planned) }} />}
              {week.done > 0 && <span className="dw-burnup-done" style={{ height: share(week.done) }} />}
            </span>
            <span className="dw-caption" aria-hidden="true">{named(index, week) ? weekDay(week.start) : ""}</span>
          </li>
        ))}
      </ol>
      <figcaption className="dw-burnup-text">
        <span>{t("goalProgressLine", { done: burnup.done, total: burnup.total })}</span>
        {burnup.ahead > 0 && <span>{t("goalProgressAheadLine", { count: burnup.ahead, day: shortDate(burnup.through, language) })}</span>}
        <span className="dw-caption dw-burnup-key"><span className="dw-burnup-swatch" aria-hidden="true" />{t("goalProgressKey", { total: burnup.total })}</span>
      </figcaption>
    </figure>
  );
}
