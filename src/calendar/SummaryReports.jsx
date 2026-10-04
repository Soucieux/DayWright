import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { formatMinutes } from "../time";
import { sectionLabel } from "./sectionLabel";

/** Report periods, and the message key naming each; All time covers every record to date. */
const PERIODS = [["day", "periodDay"], ["week", "periodWeek"], ["month", "periodMonth"], ["all", "periodAll"]];

/** The heading over a wider report's parts, by the kind of part it lists. */
const SECTION_HEADINGS = { day: "reportByDay", week: "reportByWeek", month: "reportByMonth" };

/**
 * A wider report broken down one level, newest first: a week into its days, a month into its weeks,
 * all time into its months, each with what was done by area and its own advice.
 * @param {object} props
 * @param {object[]} props.sections - The parts with a record, as the local service lists them.
 */
function ReportSections({ sections }) {
  const { t, language, demoText } = useI18n();
  return (
    <>
      <h3 className="dw-section-label dw-report-advice">{t(SECTION_HEADINGS[sections[0].periodKind])}</h3>
      <ol className="dw-report-parts">
        {sections.map((section) => (
          <li key={section.periodKey}>
            <h4>{sectionLabel(section, t, language)}</h4>
            <p className="dw-report-part-areas">
              {DOMAINS.filter((domain) => section.domains[domain]?.scheduled).map((domain) => (
                <span key={domain}><AreaTag domain={domain} plain />{t("doneOfScheduled", {
                  done: section.domains[domain].done, total: section.domains[domain].scheduled })}</span>
              ))}
            </p>
            {section.suggestions.length > 0 && (
              <ul className="dw-report-list">
                {section.suggestions.map((item, index) => (
                  <li key={`${item.domain}-${index}`}><AreaGlyph domain={item.domain} /><span>{demoText(item.content)}</span></li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </>
  );
}

/** How an area agent groups the period's tasks, in the order a report lists them, and each group's label. */
const VIEW_GROUPS = [["slipping", "reportSlipping"], ["lengthOff", "reportLengthOff"], ["going", "reportGoing"]];

/**
 * What each area agent makes of the period's tasks, from everything it knows of them: the ones that
 * keep slipping, whose length looks off, or that are going well.
 * @param {object} props
 * @param {object[]} props.views - One per area agent with something to say; see DomainAgent.outlook.
 */
function AgentsView({ views }) {
  const { t, demoText } = useI18n();
  return (
    <>
      <h4 className="dw-section-label">{t("reportAgentsView")}</h4>
      <ul className="dw-report-list">
        {views.map((view) => (
          <li key={view.agent}><AreaGlyph domain={view.agent} />
            <span>{VIEW_GROUPS.filter(([group]) => view[group].length)
              .map(([group, label]) => t("reportViewGroup", { group: t(label), tasks: view[group].map(demoText).join(t("listSeparator")) }))
              .join(" · ")}</span></li>
        ))}
      </ul>
    </>
  );
}

/**
 * One report laid out by kind instead of as a paragraph: each area's reported outcomes, what the
 * area agents make of the tasks, the tasks left partly done or skipped, and what the area records hold.
 * @param {object} props
 * @param {object} props.report - One period's Summary report.
 */
function ReportDetails({ report }) {
  const { t, language, demoText } = useI18n();
  const areas = DOMAINS.filter((domain) => report.domains?.[domain]?.scheduled);
  const unfinished = (report.taskOutcomes || []).filter((task) => task.partial + task.skipped > 0);
  const learning = report.areaEvidence?.learning;
  const life = report.areaEvidence?.life;
  const energy = life?.latestDaily?.energy_level;
  const note = life?.notes?.at(-1);
  return (
    <div className="dw-report-details">
      {areas.length > 0 && (
        <table className="dw-report-table">
          <caption className="dw-section-label">{t("reportByArea")}</caption>
          <thead>
            <tr><th scope="col">{t("reportArea")}</th><th scope="col">{t("done")}</th><th scope="col">{t("partial")}</th>
              <th scope="col">{t("skipped")}</th><th scope="col">{t("reportScheduled")}</th></tr>
          </thead>
          <tbody>
            {areas.map((domain) => {
              const counts = report.domains[domain];
              return (
                <tr key={domain}><th scope="row"><AreaTag domain={domain} plain /></th>
                  <td>{counts.done}</td><td>{counts.partial}</td><td>{counts.skipped}</td><td>{counts.scheduled}</td></tr>
              );
            })}
          </tbody>
        </table>
      )}
      {report.agentsView?.length > 0 && <AgentsView views={report.agentsView} />}
      {unfinished.length > 0 && (
        <>
          <h4 className="dw-section-label">{t("reportUnfinished")}</h4>
          <ul className="dw-report-list">
            {unfinished.map((task) => (
              <li key={`${task.domain}-${task.taskTitle}`}><AreaGlyph domain={task.domain} /><span>{demoText(task.taskTitle)}</span>
                <span className="dw-caption">{[task.partial > 0 && `${t("partial")} ${task.partial}`, task.skipped > 0 && `${t("skipped")} ${task.skipped}`].filter(Boolean).join(" · ")}</span></li>
            ))}
          </ul>
        </>
      )}
      <h4 className="dw-section-label">{t("reportRecords")}</h4>
      <dl className="dw-report-facts">
        <dt>{t("reportLearning")}</dt>
        <dd>{t("reportLearningValue", { sessions: learning?.sessions ?? 0, minutes: formatMinutes(learning?.minutes ?? 0, language), done: learning?.done ?? 0 })}</dd>
        <dt>{t("reportHabits")}</dt>
        <dd>{t("doneOfScheduled", { done: life?.habitDone ?? 0, total: life?.habitReports ?? 0 })}</dd>
        {energy != null && <><dt>{t("reportEnergy")}</dt><dd>{energy}/5</dd></>}
        {note && <><dt>{t("reportNote")}</dt><dd>{demoText(note)}</dd></>}
        <dt>{t("reportGoals")}</dt>
        <dd>{report.goals?.length ?? 0}</dd>
      </dl>
    </div>
  );
}

/**
 * Clear one area's saved advice for a week. It deletes for good, so it takes two steps and says
 * what goes and what stays.
 * @param {object} props
 * @param {string} props.week - The ISO week, such as 2026-W39.
 * @param {string} props.domain - The area whose advice is cleared.
 * @param {boolean} props.backendConnected - Whether the deletion can be saved.
 * @param {(week: string, domain: string) => Promise<void>} props.onClear - Delete the advice.
 */
function ClearWeekAdvice({ week, domain, backendConnected, onClear }) {
  const { t } = useI18n();
  const [confirming, setConfirming] = useState(false);
  const area = t(domain);
  if (!confirming) {
    return (
      <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setConfirming(true)}>
        <Icon name="trash" size={18} />{t("clearWeekOfArea", { area })}
      </button>
    );
  }
  return (
    <div className="dw-confirm-remove" role="alertdialog" aria-labelledby={`dw-clear-${domain}`} aria-describedby={`dw-clear-${domain}-body`}>
      <p className="dw-step">{t("stepTwoOfTwo")}</p>
      <h3 id={`dw-clear-${domain}`}>{t("clearWeekQuestion", { area })}</h3>
      <p id={`dw-clear-${domain}-body`}>{t("clearWeekConsequence", { area })}</p>
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-danger" onClick={() => onClear(week, domain).then(() => setConfirming(false))}>
          <Icon name="trash" size={18} />{t("clearAdviceAction")}
        </button>
        <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setConfirming(false)}>{t("cancel")}</button>
      </div>
    </div>
  );
}

/**
 * The Summary agent's reports for the selected day, its week, its month and all time: what was
 * reported by area, how the area agents see it, and the advice it saved, which the user can dismiss.
 * All time has no saved advice. Pencilled, because an agent wrote it.
 * @param {object} props
 * @param {object|null} props.reports - Reports by period, or null without the local service.
 * @param {object|null} props.pool - Saved advice by period.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {boolean} [props.dayOnly] - Show only the day's report and advice, without the period choice.
 * @param {(adviceId: string) => void} props.onDismissAdvice - Stop an idea being used.
 * @param {(week: string, domain: string) => Promise<void>} [props.onClearWeek] - Delete a week's advice for one area.
 */
export function SummaryReports({ reports, pool, backendConnected, dayOnly = false, onDismissAdvice, onClearWeek }) {
  const { t, demoText } = useI18n();
  const [kind, setKind] = useState("day");
  const report = reports?.[kind];
  const period = pool?.[kind];
  const active = (period?.items || []).filter((item) => item.status === "active");
  const reported = DOMAINS.filter((domain) => report?.domains?.[domain]?.scheduled);
  const weekAreas = [...new Set([...(period?.items || []), ...(period?.notices || [])].map((item) => item.domain))];

  return (
    <section className="dw-card dw-pencilled" aria-labelledby="dw-reports-title">
      <p className="dw-agent-line"><span className="dw-agent-mark"><Icon name="agent" size={16} /></span>
        <strong id="dw-reports-title">{t("summaryAgent")}</strong><span className="dw-caption">· {t("reportsLabel")}</span></p>
      {!dayOnly && <Segmented label={t("reportPeriod")} value={kind} onChange={setKind} options={PERIODS.map(([value, key]) => [value, t(key)])} />}
      {!report ? <p className="dw-muted dw-report-empty">{reports ? t("noReportYet") : t("reportsNeedService")}</p> : (
        <>
          <p className="dw-caption dw-report-period">{kind === "all" ? t("periodAllSoFar") : report.periodKey} · {t("recordedDaysCount", { count: report.recordedDays })}</p>
          {reported.length ? (
            <ul className="dw-balance">
              {reported.map((domain) => {
                const counts = report.domains[domain];
                return (
                  <li key={domain}>
                    <AreaTag domain={domain} plain />
                    <span className={`dw-track dw-area-${areaOf(domain)}`}><span style={{ width: `${Math.round((counts.done / counts.scheduled) * 100)}%` }} /></span>
                    <span className="dw-caption">{t("doneOfScheduled", { done: counts.done, total: counts.scheduled })}</span>
                  </li>
                );
              })}
            </ul>
          ) : <p className="dw-muted">{t("noReportedWorkYet")}</p>}
          <details className="dw-more"><summary>{t("readReport")}<Icon name="down" size={18} /></summary><ReportDetails report={report} /></details>
        </>
      )}
      {period && (
        <>
          <h3 className="dw-section-label dw-report-advice">{t("adviceHeading")}</h3>
          {active.length ? (
            <ul className="dw-advice-list">
              {active.map((item) => (
                <li key={item.id}>
                  <p className="dw-chips"><AreaTag domain={item.domain} /><span className="dw-chip dw-chip-small">{t(item.priority)}</span></p>
                  <p>{demoText(item.content)}</p>
                  <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => onDismissAdvice(item.id)}>{t("dismissAction")}</button>
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noActiveAdvice")}</p>}
          {period.notices.map((notice, index) => (
            <p key={`${notice.domain}-${index}`} className="dw-caption">{t("raisedAgain", { content: demoText(notice.content) })}</p>
          ))}
          <p className="dw-caption">{t("adviceDismissNote")}</p>
          {kind === "week" && weekAreas.map((domain) => (
            <ClearWeekAdvice key={domain} week={period.periodKey} domain={domain} backendConnected={backendConnected} onClear={onClearWeek} />
          ))}
        </>
      )}
      {!dayOnly && report?.sections?.length > 0 && <ReportSections sections={report.sections} />}
    </section>
  );
}
