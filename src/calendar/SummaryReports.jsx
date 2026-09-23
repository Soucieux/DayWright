import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";

/** Report periods, and the message key naming each. */
const PERIODS = [["day", "periodDay"], ["week", "periodWeek"], ["month", "periodMonth"]];

/** Areas in the order a report lists them. */
const REPORT_AREAS = ["learning", "life", "finance", "rest"];

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
 * The Summary agent's reports for the selected day, its week and its month: what was reported by
 * area, and the advice it saved, which the user can dismiss. Pencilled, because an agent wrote it.
 * @param {object} props
 * @param {object|null} props.reports - Reports by period, or null without the local service.
 * @param {object|null} props.pool - Saved advice by period.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(adviceId: string) => void} props.onDismissAdvice - Stop an idea being used.
 * @param {(week: string, domain: string) => Promise<void>} props.onClearWeek - Delete a week's advice for one area.
 */
export function SummaryReports({ reports, pool, backendConnected, onDismissAdvice, onClearWeek }) {
  const { t, demoText } = useI18n();
  const [kind, setKind] = useState("day");
  const report = reports?.[kind];
  const period = pool?.[kind];
  const active = (period?.items || []).filter((item) => item.status === "active");
  const reported = REPORT_AREAS.filter((domain) => report?.domains?.[domain]?.scheduled);
  const weekAreas = [...new Set([...(period?.items || []), ...(period?.notices || [])].map((item) => item.domain))];

  return (
    <section className="dw-card dw-pencilled" aria-labelledby="dw-reports-title">
      <p className="dw-agent-line"><span className="dw-agent-mark"><Icon name="agent" size={16} /></span>
        <strong id="dw-reports-title">{t("summaryAgent")}</strong><span className="dw-caption">· {t("reportsLabel")}</span></p>
      <Segmented label={t("reportPeriod")} value={kind} onChange={setKind} options={PERIODS.map(([value, key]) => [value, t(key)])} />
      {!report ? <p className="dw-muted dw-report-empty">{reports ? t("noReportYet") : t("reportsNeedService")}</p> : (
        <>
          <p className="dw-caption dw-report-period">{report.periodKey} · {t("recordedDaysCount", { count: report.recordedDays })}</p>
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
          {report.text && <details className="dw-more"><summary>{t("readReport")}</summary><p className="dw-muted">{demoText(report.text)}</p></details>}
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
    </section>
  );
}
