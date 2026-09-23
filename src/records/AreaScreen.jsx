import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { StatusControl } from "../ui/StatusControl";
import { fullDate } from "../time";
import { dayRows } from "../today/dayRows";
import { LearnArea } from "./LearnArea";
import { LifeArea } from "./LifeArea";
import { MoneyArea } from "./MoneyArea";

/** Each area's tabs in order, with the message key naming each. */
const AREA_TABS = {
  learning: [["overview", "tabOverview"], ["sessions", "tabSessions"], ["subjects", "tabSubjects"], ["tasks", "tabTasks"]],
  life: [["overview", "tabOverview"], ["checkin", "tabCheckIn"], ["habits", "tabHabits"], ["events", "tabEvents"], ["tasks", "tabTasks"]],
  finance: [["overview", "tabOverview"], ["balance", "tabBalance"], ["transactions", "tabTransactions"], ["budgets", "tabBudgets"], ["tasks", "tabTasks"]],
};

/** Each area's name, the domains its tasks come from, and the report its header offers. */
const AREAS = {
  learning: { title: "learning", domains: ["learning"], primary: ["session", "recordSessionAction"] },
  life: { title: "lifeAndRest", domains: ["life", "rest"], primary: ["checkin", "checkInAction"] },
  finance: { title: "finance", domains: ["finance"], primary: ["transaction", "recordTransactionAction"] },
};

/** The area screen each domain shows. */
const AREA_CONTENT = { learning: LearnArea, life: LifeArea, finance: MoneyArea };

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
              {past ? <span className="dw-area-task-title">{demoText(row.title)}<span className="dw-caption">{row.start_time}</span></span> : (
                <button type="button" className="dw-area-task-title" aria-label={`${demoText(row.title)}, ${row.start_time}. ${t("openDetails")}`} onClick={() => onOpenRow(row)}>
                  {demoText(row.title)}<span className="dw-caption">{row.start_time}</span>
                </button>
              )}
              <StatusControl value={row.completion_status} title={demoText(row.title)} readOnly={past} disabled={!backendConnected}
                onChange={(status) => onStatus(row, status)} />
            </li>
          ))}
        </ul>
      ) : <p className="dw-muted">{t("noAreaTasks")}</p>}
    </section>
  );
}

/**
 * One area of Records: its own reports and catalogues in tabs, and its tasks for the day on show.
 * Reports are for today only; a past day is history.
 * @param {object} props
 * @param {"learning"|"life"|"finance"} props.domain - The area.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onRecords - Go back to Records.
 * @param {() => void} props.onToday - Show today's records instead.
 * @param {(domain: string) => void} props.onAddTask - Record a task in this area.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {() => Promise<void>} props.onAreaSaved - Refresh the day and month after a change.
 */
export function AreaScreen({ domain, day, today, backendConnected, onRecords, onToday, onAddTask, onOpenRow, onStatus, onAreaSaved }) {
  const { t, language } = useI18n();
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState(null);
  const tabRefs = useRef({});
  const area = AREAS[domain];
  const tabs = AREA_TABS[domain];
  const Content = AREA_CONTENT[domain];
  const url = `/api/areas/${domain}?${new URLSearchParams({ date: day.date })}`;
  const past = day.date < today;
  const isToday = day.date === today;
  const rows = dayRows(day).rows.filter((row) => area.domains.includes(row.domain));

  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    api(url).then((result) => live && setData(result)).catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [url, backendConnected]);

  /** Save a change, then show the area and the day as they now are. Throws when saving fails. */
  async function mutate(path, method, body) {
    await api(path, { method, body: JSON.stringify(body) });
    setData(await api(url));
    await onAreaSaved();
  }

  /** Save a change from a button on the page, showing any failure on the page. */
  function act(path, method, body) {
    setError("");
    mutate(path, method, body).catch((caught) => setError(caught.message));
  }

  function onTabKey(event) {
    const index = tabs.findIndex(([id]) => id === tab);
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const [next] = tabs[(index + step + tabs.length) % tabs.length];
    setTab(next);
    tabRefs.current[next]?.focus();
  }

  const tasks = (
    <AreaTasks rows={rows} past={past} backendConnected={backendConnected} onOpenRow={onOpenRow} onStatus={onStatus}
      onAddTask={() => onAddTask(area.domains[0])} title={t("tasksInArea", { area: t(area.title) })} />
  );

  return (
    <main className="dw-page" tabIndex={-1}>
      <button type="button" className="dw-back" onClick={onRecords}><Icon name="left" size={18} />{t("navRecords")} / {t("areasHeading")}</button>
      <header className="dw-page-head">
        <h1 className="dw-display dw-area-title">
          {area.domains.map((value) => <AreaGlyph key={value} domain={value} />)}{t(area.title)}
        </h1>
        {isToday && (
          <div className="dw-page-actions">
            <button type="button" className="dw-button" disabled={!backendConnected || !data} onClick={() => setSheet(area.primary[0])}>
              <Icon name="plus" size={18} />{t(area.primary[1])}
            </button>
          </div>
        )}
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      {!isToday && (
        <p className={`dw-banner ${past ? "dw-banner-history" : "dw-banner-caution"}`} role="note">
          <Icon name={past ? "lock" : "calendar"} size={18} />
          <span>{t(past ? "areaPastDay" : "areaFutureDay", { date: fullDate(day.date, language) })}</span>
          <button type="button" className="dw-link" onClick={onToday}>{t("showTodayAction")}</button>
        </p>
      )}
      <div className="dw-tabs" role="tablist" aria-label={t(area.title)} onKeyDown={onTabKey}>
        {tabs.map(([id, key]) => (
          <button key={id} ref={(node) => { tabRefs.current[id] = node; }} type="button" role="tab" id={`dw-tab-${id}`}
            aria-selected={tab === id} aria-controls="dw-area-panel" tabIndex={tab === id ? 0 : -1} onClick={() => setTab(id)}>{t(key)}</button>
        ))}
      </div>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div id="dw-area-panel" role="tabpanel" aria-labelledby={`dw-tab-${tab}`} className={tab === "overview" ? "dw-area-grid" : "dw-area-single"}>
        {tab !== "tasks" && !backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("areaNeedsService")}</p>}
        {tab !== "tasks" && backendConnected && !data && <p className="dw-muted">{t("loadingArea")}</p>}
        {data && <Content tab={tab} data={data} isToday={isToday} canPrepare={day.date >= today} backendConnected={backendConnected}
          mutate={mutate} act={act} sheet={sheet} setSheet={setSheet} />}
        {(tab === "overview" || tab === "tasks") && tasks}
      </div>
      {!isToday && <p className="dw-caption dw-area-note"><AreaTag domain={area.domains[0]} plain /> {t("areaReportsToday")}</p>}
    </main>
  );
}
