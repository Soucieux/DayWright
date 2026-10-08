import { Fragment, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { barTime } from "../records/areaOverview";
import { AvaOnly } from "../settings/NeedsModel";
import { GraphTips } from "../ui/GraphTips";
import { Segmented } from "../ui/Segmented";
import { Lead, PairList, PatternCard } from "./PatternParts";
import {
  ENERGY_DAYS, ENERGY_GROUPS, bestHoursLead, catchUpDay, cellLabel, checkPrompt, columnLabel, columnName, energyLead, estimatesLead,
  heatKey, minutesText, outcomeLead, pairsLead, rangeCaption, reportingLead, timeText, toCheckNote, weekdayNames,
} from "./patternText";

/** The ranges the tab reads, Month first on show, each with its words by message key. */
const PERIODS = [["week", "periodWeek"], ["month", "periodMonth"], ["all", "periodAll"]];
/** Time by outcome's parts, from fully done at the base, each with its status's words. */
const OUTCOME_PARTS = [["done", "done"], ["partial", "partial"], ["skipped", "skipped"], ["noReply", "noReply"], ["dayPaused", "dayPaused"]];
/** Reporting habit's parts, each with its class and words. */
const REPORT_PARTS = [["rightAway", "dw-report-now", "patternsRightAway"], ["laterDay", "dw-report-later", "patternsLaterDay"],
  ["nextDay", "dw-report-nextday", "patternsNextDay"], ["noReply", "dw-follow-noReply", "patternsNoReplyShort"]];
/** Beyond this many columns of weeks or months a graph names only its first, current and last. */
const NAMED_COLUMNS = 8;
/** Energy and real time's bar reaches the track's end at this many percent from plan. */
const DIVERGE_LIMIT = 50;
/** The caption under Time by outcome, by what its columns are. */
const OUTCOME_CAPTIONS = { day: "patternOutcomeCaptionDay", week: "patternOutcomeCaptionWeek", month: "patternOutcomeCaptionMonth" };

/** Whether a column's name shows under it: every day's, and up to NAMED_COLUMNS weeks or months, else the first, current and last. */
const named = (index, columns) => columns.length <= NAMED_COLUMNS || columns[0].kind === "day" || index === 0
  || index === columns.length - 1 || columns[index].current;

/**
 * A graph's columns' list class: seven days share the usual grid, a month of days the narrow one, and
 * weeks or months their own count.
 * @param {object[]} columns - The columns.
 * @returns {{className: string, style: object}} Its class and the column count it sets.
 */
function columnsLayout(columns) {
  if (columns[0]?.kind === "day") return { className: `dw-graph-bars${columns.length > 7 ? " dw-graph-bars-month" : ""}`, style: {} };
  return { className: "dw-graph-bars dw-graph-bars-weeks", style: { "--cols": columns.length } };
}

/**
 * Best hours: a grid of weekdays by the hours used, each cell's shade one of four steps split by the busiest,
 * its count in its words and tip; the best window's hours bold and underlined; a key in counts.
 * @param {object} props
 * @param {object} props.graph - As patterns.best_hours gives it.
 */
function BestHours({ graph }) {
  const { t, language } = useI18n();
  const names = weekdayNames(language);
  const key = heatKey(graph.key, t);
  return (
    <>
      {graph.finding && <Lead parts={bestHoursLead(graph.finding, t, language)} />}
      <GraphTips label={t("patternsHeatLabel")} columns={graph.hours.length}>
        <div className="dw-heat" style={{ "--hours": graph.hours.length }}>
          <span aria-hidden="true" />
          {graph.hours.map((hour, index) => (
            <span key={hour} className={`dw-heat-hour${graph.best.includes(hour) ? " is-best" : ""}`} aria-hidden="true">
              {index % 2 ? "" : String(hour).padStart(2, "0")}
            </span>
          ))}
          {names.map((name, weekday) => (
            <Fragment key={name}>
              <span className="dw-heat-day" aria-hidden="true">{name}</span>
              {graph.hours.map((hour, index) => (
                <span key={hour} className={`dw-heat-cell dw-heat-${graph.steps[weekday][index]}`} role="img" data-mark
                  aria-label={cellLabel(weekday, hour, graph.cells[weekday][index], t, language)} />
              ))}
            </Fragment>
          ))}
        </div>
      </GraphTips>
      <ul className="dw-scale-key">
        <li><span className="dw-scale-swatch dw-heat-cell" aria-hidden="true" />{t("patternsNone")}</li>
        {key.steps.map((step, index) => (
          <li key={step}><span className={`dw-scale-swatch dw-heat-${graph.key[index].step}`} aria-hidden="true" />{step}</li>
        ))}
        <li className="dw-caption">{key.unit}</li>
      </ul>
    </>
  );
}

/**
 * Energy and real time: a row per energy group, its bar growing from "as planned", right for longer and left
 * for shorter, the group the finding is about in ink; a group with too few days says how many it needs.
 * @param {object} props
 * @param {object} props.graph - As patterns.energy gives it.
 */
function EnergyRows({ graph }) {
  const { t } = useI18n();
  const change = (percent) => (percent > 0 ? t("patternsLongerBy", { percent }) : percent < 0 ? t("patternsShorterBy", { percent: -percent })
    : t("patternsAsPlannedBy"));
  return (
    <>
      {graph.finding && <Lead parts={energyLead(graph.finding, t)} />}
      <GraphTips label={t("patternsEnergyLabel")}>
        <ul className="dw-diverge" aria-label={t("patternsEnergyLabel")}>
          {graph.groups.map((group) => {
            const names = ENERGY_GROUPS[group.group];
            return (
              <li key={group.group} data-mark aria-label={t("patternsEnergyRow", { group: t(names.name), count: group.days,
                change: group.percent == null ? t("patternsNotEnoughDays") : change(group.percent) })}>
                <span className="dw-diverge-name"><span>{t(names.name)}</span>
                  <span className="dw-caption">{group.days === 1 ? t("patternsGroupDaysOne", { range: names.range })
                    : t("patternsGroupDays", { range: names.range, count: group.days })}</span></span>
                {group.percent == null
                  ? <span className="dw-caption dw-diverge-needs">{t("patternsEnergyNeeds", { threshold: ENERGY_DAYS, count: group.days })}</span>
                  : (
                    <>
                      <span className="dw-diverge-track" aria-hidden="true">
                        <span className={`dw-diverge-bar ${group.percent >= 0 ? "is-over" : "is-under"}${graph.focus === group.group ? "" : " is-quiet"}`}
                          style={{ width: `${Math.min(Math.abs(group.percent), DIVERGE_LIMIT)}%` }} />
                      </span>
                      <span className="dw-diverge-value" aria-hidden="true">{group.percent > 0 ? "+" : group.percent < 0 ? "−" : ""}{Math.abs(group.percent)}%</span>
                    </>
                  )}
              </li>
            );
          })}
        </ul>
      </GraphTips>
      <p className="dw-diverge-axis" aria-hidden="true"><span className="dw-diverge-ticks">
        <span>−{DIVERGE_LIMIT}%</span><span>{t("patternsAsPlanned")}</span><span>+{DIVERGE_LIMIT}%</span></span></p>
    </>
  );
}

/**
 * Estimates improving: a column per day or week of the average gap between estimate and real time, with a
 * dash and no bar where no estimated task was fully done.
 * @param {object} props
 * @param {object} props.graph - As patterns.estimates gives it.
 * @param {string} props.today - Today, YYYY-MM-DD.
 */
function Estimates({ graph, today }) {
  const { t, language } = useI18n();
  const { columns } = graph;
  const most = Math.max(1, ...columns.map((column) => column.minutes ?? 0));
  const layout = columnsLayout(columns);
  return (
    <>
      {graph.finding && <Lead parts={estimatesLead(graph.finding, columns, today, t, language)} />}
      <GraphTips label={t("patternsEstLabel")}>
        <ol className={layout.className} style={layout.style} aria-label={t("patternsEstLabel")}>
          {columns.map((column, index) => (
            <li key={column.start} className={column.current ? "dw-load-today" : undefined} data-mark
              aria-label={column.minutes == null ? t("patternsEstNone", { when: columnLabel(column, t, language) })
                : t("patternsEstColumn", { when: columnLabel(column, t, language), minutes: minutesText(column.minutes, language) })}>
              {columns.length <= 7 && <span className="dw-caption dw-load-value" aria-hidden="true">
                {column.minutes == null ? "–" : minutesText(column.minutes, language)}</span>}
              <span className="dw-graph-bar" aria-hidden="true">
                {column.minutes != null && <span className="dw-graph-fill" style={{ height: `${(column.minutes / most) * 100}%` }} />}
              </span>
              <span className="dw-caption" aria-hidden="true">{named(index, columns) ? columnName(column, columns, language) : ""}</span>
            </li>
          ))}
        </ol>
      </GraphTips>
    </>
  );
}

/**
 * Time by outcome: a column per day, week or month of the time tasks took, stacked by the status each got
 * and scaled to the busiest, its total above it; a key with each part's time, the paused one only when any.
 * @param {object} props
 * @param {object} props.graph - As patterns.outcome gives it.
 */
function Outcome({ graph }) {
  const { t, language } = useI18n();
  const { columns } = graph;
  const layout = columnsLayout(columns);
  const parts = OUTCOME_PARTS.filter(([part]) => part !== "dayPaused" || graph.totals.dayPaused);
  const words = (column) => parts.filter(([part]) => column.parts[part])
    .map(([part, key]) => `${t(key)} ${timeText(column.parts[part], language)}`).join(t("listSeparator"));
  return (
    <>
      {graph.finding && <Lead parts={outcomeLead(graph.finding, t, language)} />}
      <GraphTips label={t("patternsOutcomeLabel")}>
        <ol className={layout.className} style={layout.style} aria-label={t("patternsOutcomeLabel")}>
          {columns.map((column, index) => (
            <li key={column.start} className={column.current ? "dw-load-today" : undefined} data-mark
              aria-label={t("patternsOutcomeColumn", { when: columnLabel(column, t, language), parts: column.total ? words(column) : t("patternsNone") })}>
              {columns.length <= 7 && <span className="dw-caption dw-load-value" aria-hidden="true">{barTime(column.total)}</span>}
              <span className="dw-graph-bar" aria-hidden="true">
                {parts.filter(([part]) => column.parts[part]).map(([part]) => (
                  <span key={part} className={`dw-follow-part dw-follow-${part}`} style={{ height: `${(column.parts[part] / graph.busiest) * 100}%` }} />
                ))}
              </span>
              <span className="dw-caption" aria-hidden="true">{named(index, columns) ? columnName(column, columns, language) : ""}</span>
            </li>
          ))}
        </ol>
      </GraphTips>
      <ul className="dw-follow-key dw-pattern-key">
        {parts.map(([part, key]) => (
          <li key={part}><span className={`dw-follow-swatch dw-follow-${part}`} aria-hidden="true" />{t(key)} <strong>{timeText(graph.totals[part], language)}</strong></li>
        ))}
      </ul>
    </>
  );
}

/**
 * Reporting habit: a bar per week, or per day in a week, of when statuses were set, with the share set
 * right away at the right; a key with each part's count.
 * @param {object} props
 * @param {object} props.graph - As patterns.reporting gives it.
 * @param {string} props.today - Today, YYYY-MM-DD.
 */
function Reporting({ graph, today }) {
  const { t, language } = useI18n();
  const { columns } = graph;
  const short = new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "short" });
  const rowName = (column) => (column.kind === "day" ? short.format(new Date(`${column.start}T12:00:00`)) : columnName(column, columns, language));
  return (
    <>
      {graph.finding && <Lead parts={reportingLead(graph.finding, columns, today, t, language)} />}
      <GraphTips label={t("patternsReportLabel")}>
        <ul className="dw-share-rows" aria-label={t("patternsReportLabel")}>
          {columns.filter((column) => column.total).map((column) => (
            <li key={column.start} data-mark aria-label={t("patternsReportColumn", { when: columnLabel(column, t, language),
              parts: REPORT_PARTS.filter(([part]) => column.shares[part]).map(([part, , key]) => `${t(key)} ${column.shares[part]}%`).join(t("listSeparator")) })}>
              <span className={`dw-caption${column.current ? " is-current" : ""}`} aria-hidden="true">{rowName(column)}</span>
              <span className="dw-share-bar" aria-hidden="true">
                {REPORT_PARTS.filter(([part]) => column.counts[part]).map(([part, className]) => (
                  <span key={part} className={`dw-share-part ${className}`} style={{ flex: `${column.shares[part]} 1 0` }} />
                ))}
              </span>
              <span className="dw-share-value" aria-hidden="true">{column.shares.rightAway}%</span>
            </li>
          ))}
        </ul>
      </GraphTips>
      <ul className="dw-follow-key dw-pattern-key">
        {REPORT_PARTS.map(([part, className, key]) => (
          <li key={part}><span className={`dw-follow-swatch ${className}`} aria-hidden="true" /><strong>{graph.totals[part]}</strong>{t(key)}</li>
        ))}
      </ul>
    </>
  );
}

/**
 * Calendar's Patterns tab: what the times you recorded show, over the week, the thirty days or all the time
 * up to the day on show. Under the switch, its range and, when any are left out, the times still to check,
 * which Ava checks; then the graphs in three groups. The graphs on show stay, faded, while another range
 * loads; without the local service, a line says Patterns need it.
 * @param {object} props
 * @param {string} props.date - The day on show, YYYY-MM-DD.
 * @param {object} props.stamp - The day on show as last loaded; a fresh one, after a change, reads the times again.
 * @param {string} props.today - Today, YYYY-MM-DD.
 * @param {boolean} props.backendConnected - Whether the local service is running.
 * @param {(text: string, send?: boolean, date?: string) => void} props.onAskAva - Ask Ava, sending the words at once,
 *   from the day given.
 */
export function PatternsPanel({ date, stamp, today, backendConnected, onAskAva }) {
  const { t, language } = useI18n();
  const [period, setPeriod] = useState("month");
  const [tab, setTab] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    setLoading(true);
    api(`/api/patterns?${new URLSearchParams({ date, period })}`)
      .then((found) => { if (live) { setTab(found); setError(""); } })
      .catch((caught) => { if (live) setError(caught.message); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [date, period, backendConnected, stamp]);

  if (!backendConnected) return <section className="dw-card"><p className="dw-muted">{t("patternsServiceOff")}</p></section>;
  const card = (id, graph, title, caption, body, instead = null) => (
    <PatternCard id={`dw-pattern-${id}`} graph={graph} title={t(title)} gauge={tab[graph]} period={tab.period} caption={caption} instead={instead}>
      {body}
    </PatternCard>
  );
  return (
    <div className="dw-patterns">
      <Segmented label={t("patternsPeriod")} value={period} onChange={setPeriod} options={PERIODS.map(([value, key]) => [value, t(key)])} />
      {error && <p className="dw-alert" role="alert">{error}</p>}
      {!tab ? <p className="dw-muted">{t("patternsLoading")}</p> : (
        <div className={`dw-patterns-body${loading ? " is-loading" : ""}`} aria-busy={loading}>
          <p className="dw-caption dw-patterns-range">{rangeCaption(tab, t, language)}</p>
          {tab.toCheck > 0 && (
            <p className="dw-pattern-note"><span className="dw-caption">{toCheckNote(tab.toCheck, tab.needsStatus, t)}</span>
              <AvaOnly>
                <span className="dw-pattern-note-actions">
                  <button type="button" className="dw-button dw-button-quiet" onClick={() => onAskAva(checkPrompt(tab.period, t), true)}>
                    {t("patternsAskAva")}</button>
                  {tab.needsStatus > 0 && (
                    <button type="button" className="dw-button dw-button-quiet" onClick={() => onAskAva(t("catchUpPrompt"), true, catchUpDay(tab.checks))}>
                      {t("catchUpAction")}</button>
                  )}
                </span>
              </AvaOnly></p>
          )}
          <h3 className="dw-section-label dw-patterns-group">{t("patternsGroupWork")}</h3>
          {card("best", "bestHours", "patternBestHours", t("patternBestHoursCaption"), <BestHours graph={tab.bestHours} />)}
          {card("energy", "energy", "patternEnergy", t("patternEnergyCaption"), <EnergyRows graph={tab.energy} />,
            tab.energy.finding?.kind === "never" ? t("patternsEnergyNever") : null)}
          <h3 className="dw-section-label dw-patterns-group">{t("patternsGroupLength")}</h3>
          {card("pairs", "plannedActual", "patternPairs", t("patternPairsCaption"), (
            <>
              {tab.plannedActual.finding && <Lead parts={pairsLead(tab.plannedActual.finding, t, language)} />}
              <PairList rows={tab.plannedActual.rows} label={t("patternsPairsLabel")} />
            </>
          ))}
          {card("estimates", "estimates", "patternEstimates", tab.estimates.columns.length <= 7
            && tab.estimates.columns.some((column) => column.minutes == null)
            ? `${t("patternEstimatesCaption")} ${t("patternEstimatesDash")}` : t("patternEstimatesCaption"),
          <Estimates graph={tab.estimates} today={today} />)}
          {card("outcome", "outcome", "patternOutcome", t(OUTCOME_CAPTIONS[tab.outcome.columns[0]?.kind || "week"]), <Outcome graph={tab.outcome} />)}
          <h3 className="dw-section-label dw-patterns-group">{t("patternsGroupReport")}</h3>
          {card("reporting", "reporting", "patternReporting", t("patternReportingCaption"), <Reporting graph={tab.reporting} today={today} />)}
        </div>
      )}
    </div>
  );
}
