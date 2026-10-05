import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { StatusControl } from "../ui/StatusControl";
import { fullDate } from "../time";
import { dayRows } from "../today/dayRows";
import { AreaOverview } from "./OverviewCards";

/** Every area's tabs in order, with the message key naming each. */
const AREA_TABS = [["overview", "tabOverview"], ["tasks", "tabTasks"]];

/**
 * The area's tasks for the day on show, each with its status; they open their details unless the
 * day has passed.
 * @param {object} props
 * @param {object[]} props.rows - The area's rows.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {() => void} props.onAddTask - Record a task in this area.
 * @param {string} props.title - The card's heading.
 */
function AreaTasks({ rows, past, backendConnected, onOpenRow, onStatus, onAddTask, title }) {
  const { t, demoText } = useI18n();
  return (
    <section className="dw-card" aria-labelledby="dw-area-tasks">
      <div className="dw-card-head">
        <h2 id="dw-area-tasks" className="dw-heading">{title}</h2>
        {!past && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addAction")}</button>}
      </div>
      {rows.length ? (
        <ul className="dw-area-tasks">
          {rows.map((row) => (
            <li key={`${row.kind}-${row.id}`}>
              <AreaGlyph domain={row.domain} />
              {past ? <span className="dw-area-task-title">{demoText(row.title)}<span className="dw-caption">{row.start_time || t("noStartTime")}</span></span> : (
                <button type="button" className="dw-area-task-title" aria-label={`${demoText(row.title)}, ${row.start_time || t("noStartTime")}. ${t("openDetails")}`} onClick={() => onOpenRow(row)}>
                  {demoText(row.title)}<span className="dw-caption">{row.start_time || t("noStartTime")}</span>
                </button>
              )}
              <StatusControl value={row.completion_status} title={demoText(row.title)} readOnly={past} disabled={!backendConnected}
                paused={row.source?.goalStatus === "paused"} onChange={(status) => onStatus(row, status)} />
            </li>
          ))}
        </ul>
      ) : <p className="dw-muted">{t("noAreaTasks")}</p>}
    </section>
  );
}

/**
 * One area of Records: its overview of the day on show, built from its tasks, goals and repeats, and
 * its tasks for that day. Reports are for today only; a past day is history.
 * @param {object} props
 * @param {"learning"|"life"|"work"|"project"} props.domain - The area.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onRecords - Go back to Records.
 * @param {() => void} props.onToday - Show today's records instead.
 * @param {(defaults: {domain: string, goalId?: string}) => void} props.onAddTask - Record a task in this area, for a goal or none.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 */
export function AreaScreen({ domain, day, today, backendConnected, onRecords, onToday, onAddTask, onOpenRow, onStatus }) {
  const { t, language } = useI18n();
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const tabRefs = useRef({});
  const url = `/api/areas/${domain}?${new URLSearchParams({ date: day.date })}`;
  const past = day.date < today;
  const isToday = day.date === today;
  const rows = dayRows(day).rows.filter((row) => row.domain === domain);

  // The overview is built from the day's tasks, so it is read again whenever the day changes.
  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    api(url).then((result) => live && setData(result)).catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [url, backendConnected, day]);

  function onTabKey(event) {
    const index = AREA_TABS.findIndex(([id]) => id === tab);
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const [next] = AREA_TABS[(index + step + AREA_TABS.length) % AREA_TABS.length];
    setTab(next);
    tabRefs.current[next]?.focus();
  }

  const tasks = (
    <AreaTasks rows={rows} past={past} backendConnected={backendConnected} onOpenRow={onOpenRow} onStatus={onStatus}
      onAddTask={() => onAddTask({ domain })} title={t("tasksInArea", { area: t(domain) })} />
  );

  return (
    <main className="dw-page" tabIndex={-1}>
      <button type="button" className="dw-back" onClick={onRecords}><Icon name="left" size={18} />{t("navRecords")} / {t("areasHeading")}</button>
      <header className="dw-page-head">
        <h1 className="dw-display dw-area-title"><AreaGlyph domain={domain} />{t(domain)}</h1>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      {!isToday && (
        <p className={`dw-banner ${past ? "dw-banner-history" : "dw-banner-caution"}`} role="note">
          <Icon name={past ? "lock" : "calendar"} size={18} />
          <span>{t(past ? "areaPastDay" : "areaFutureDay", { date: fullDate(day.date, language) })}</span>
          <button type="button" className="dw-link" onClick={onToday}>{t("showTodayAction")}</button>
        </p>
      )}
      <div className="dw-tabs" role="tablist" aria-label={t(domain)} onKeyDown={onTabKey}>
        {AREA_TABS.map(([id, key]) => (
          <button key={id} ref={(node) => { tabRefs.current[id] = node; }} type="button" role="tab" id={`dw-tab-${id}`}
            aria-selected={tab === id} aria-controls="dw-area-panel" tabIndex={tab === id ? 0 : -1} onClick={() => setTab(id)}>{t(key)}</button>
        ))}
      </div>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-page-body">
      <div id="dw-area-panel" role="tabpanel" aria-labelledby={`dw-tab-${tab}`} className={tab === "overview" ? "dw-area-grid" : "dw-area-single"}>
        {tab === "overview" && !backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("areaNeedsService")}</p>}
        {tab === "overview" && backendConnected && !data && <p className="dw-muted">{t("loadingArea")}</p>}
        {tab === "overview" && data && <AreaOverview domain={domain} data={data} canAdd={backendConnected} onAddTask={onAddTask} />}
        {tasks}
      </div>
      {!isToday && <p className="dw-caption dw-area-note"><AreaTag domain={domain} plain /> {t("areaReportsToday")}</p>}
      </div>
    </main>
  );
}
