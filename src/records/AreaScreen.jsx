import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { areaLinks } from "../library/libraryData";
import { ActionMenu } from "../ui/ActionMenu";
import { AreaGlyph, AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { fullDate } from "../time";
import {
  CarryOversCard, EnergyCard, HabitsCard, LibraryCard, LoadCard, MeetingsCard, NextStepsCard, NotesCard, PracticeCard, ProjectsCard,
  RecentlyDoneCard, ShapeCard, SubjectsCard, TodayCard,
} from "./AreaCards";
import { GoalSheet } from "./GoalsScreen";
import { AREA_ADD_CHOICES, AREA_MEANINGS } from "./areaOverview";

/**
 * One area of Records, as one page of cards in two columns: first the day on show in the area and
 * its agent's notes, the same in every area, then the area's own cards, each built by the local
 * service from its tasks, goals and repeats, and last its Library. Reports are for today only; a
 * past day is history. A goal's row opens its Edit sheet here. Everything is added from one + Add at
 * the top, whose menu starts a task, a goal, or a note or file in the area; no card adds anything.
 * @param {object} props
 * @param {"learning"|"life"|"work"|"project"} props.domain - The area.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onRecords - Go back to Records.
 * @param {() => void} props.onToday - Show today's records instead.
 * @param {() => void} props.onTodayScreen - Go to Today.
 * @param {(defaults: {domain: string}) => void} props.onAddTask - Record a task in this area, with no goal.
 * @param {(row: object) => void} props.onOpenRow - Show a row of the day on show.
 * @param {(item: {id: string, date: string}) => void} props.onOpenTask - Show a task on any day.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {() => void} props.onSeeAll - Show the area's tasks in Tasks.
 * @param {(text?: string) => void} props.onAskAva - Open Ava, with a request typed in and not sent.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSaveGoal - Save a goal.
 * @param {(item: object) => void} props.onEditTask - Edit one of a goal's tasks.
 * @param {(item: object) => Promise<void>} props.onRemoveTask - Delete one of a goal's past tasks.
 * @param {object[]|null} props.library - The Library's notes and files, newest first; null until they load.
 * @param {(links: {domain: string, goalId: string|null}) => void} props.onAddToLibrary - Add a note or file linked to the area, or to a goal from its sheet.
 * @param {() => void} props.onSeeLibrary - Show the area's notes and files in the Library.
 * @param {boolean} props.sheetOpen - Whether a task's sheet or the Library's add sheet is on show, over a goal's.
 */
export function AreaScreen({ domain, day, today, backendConnected, onRecords, onToday, onTodayScreen, onAddTask, onOpenRow, onOpenTask,
  onStatus, onSeeAll, onAskAva, onSaveGoal, onEditTask, onRemoveTask, library, onAddToLibrary, onSeeLibrary, sheetOpen }) {
  const { t, language } = useI18n();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(undefined);
  const url = `/api/areas/${domain}?${new URLSearchParams({ date: day.date })}`;
  const past = day.date < today;
  const isToday = day.date === today;

  // The cards are built from the day's tasks, so they are read again whenever the day changes.
  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    api(url).then((result) => live && setData(result)).catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [url, backendConnected, day]);

  const editingGoal = editing && (day.goals.find((goal) => goal.id === editing.id) || editing);
  const shared = { data, onOpenTask };
  const goals = { onEditGoal: (goalId) => setEditing(day.goals.find((goal) => goal.id === goalId) || null) };
  // The one + Add: a task or goal in the area, or a note or file in it, each starting with no goal.
  const add = { task: () => onAddTask({ domain }), goal: () => setEditing({ newIn: domain }), note: () => onAddToLibrary(areaLinks(domain)) };
  const own = data && ({
    learning: [<SubjectsCard key="subjects" {...shared} {...goals} onSeeAll={onSeeAll} />, <PracticeCard key="practice" {...shared} />],
    life: [<HabitsCard key="habits" {...shared} />, <ShapeCard key="shape" data={data} day={day} today={today} onOpenTask={onOpenTask} />,
      <EnergyCard key="energy" data={data} onTodayScreen={onTodayScreen} />],
    work: [<LoadCard key="load" {...shared} />, <MeetingsCard key="meetings" {...shared} />,
      <CarryOversCard key="carry" data={data} onOpenTask={onOpenTask} onAskAva={onAskAva} onSeeAll={onSeeAll} />],
    project: [<ProjectsCard key="projects" {...shared} {...goals} />, <NextStepsCard key="next" {...shared} />,
      <RecentlyDoneCard key="recent" data={data} onOpenTask={onOpenTask} onSeeAll={onSeeAll} />],
  })[domain];

  return (
    <main className="dw-page" tabIndex={-1}>
      <button type="button" className="dw-back" onClick={onRecords}><Icon name="left" size={18} />{t("navRecords")} / {t("areasHeading")}</button>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <h1 className="dw-display dw-area-title"><AreaGlyph domain={domain} />{t(domain)}</h1>
        </div>
        <div className="dw-page-actions dw-area-actions">
          <ActionMenu label={t("areaAddLabel", { area: t(domain) })} text={t("addAction")} disabled={!backendConnected}
            items={AREA_ADD_CHOICES.map(([value, key, icon]) => ({ value, label: t(key), icon }))} onChoose={(choice) => add[choice]()} />
        </div>
      </header>
      <p className="dw-area-purpose">{t(AREA_MEANINGS[domain])}</p>
      <PageBanners day={day} backendConnected={backendConnected} />
      {!isToday && (
        <p className={`dw-banner ${past ? "dw-banner-history" : "dw-banner-caution"}`} role="note">
          <Icon name={past ? "lock" : "calendar"} size={18} />
          <span>{t(past ? "areaPastDay" : "areaFutureDay", { date: fullDate(day.date, language) })}</span>
          <button type="button" className="dw-link" onClick={onToday}>{t("showTodayAction")}</button>
        </p>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
      {!backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("areaNeedsService")}</p>}
      <div className="dw-page-body">
        <div className="dw-area-grid">
          <TodayCard domain={domain} day={day} today={today} backendConnected={backendConnected} onOpenRow={onOpenRow}
            onStatus={onStatus} onSeeAll={onSeeAll} />
          {data ? <NotesCard domain={domain} notes={data.notes} today={today} onToday={onToday} onAskAva={() => onAskAva()} />
            : backendConnected && <p className="dw-muted">{t("loadingArea")}</p>}
          {own}
          <LibraryCard domain={domain} items={library} goals={day.goals} onSeeLibrary={onSeeLibrary} />
        </div>
        {!isToday && <p className="dw-caption dw-area-note"><AreaTag domain={domain} plain /> {t("areaReportsToday")}</p>}
      </div>
      {editing !== undefined && (
        <GoalSheet key={editing?.id || "new"} goal={editing?.newIn ? null : editingGoal} today={today} backendConnected={backendConnected}
          hidden={sheetOpen} atTasks={false} defaultDomain={editing?.newIn || domain} library={library} onSave={onSaveGoal} onEditTask={onEditTask}
          onDeleteTask={onRemoveTask} onAddToLibrary={onAddToLibrary} onClose={() => setEditing(undefined)} />
      )}
    </main>
  );
}
