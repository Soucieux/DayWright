import { Children, useEffect, useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { api } from "../api";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { ActionMenu } from "../ui/ActionMenu";
import { AreaGlyph, AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { TabList } from "../ui/TabList";
import { PHONE_WIDTH, useViewport } from "../ui/viewport";
import { fullDate } from "../time";
import {
  CarryOversCard, EnergyCard, HabitsCard, LibraryCard, LoadCard, MeetingsCard, NextStepsCard, NotesCard, PracticeCard, ProjectsCard,
  RecentlyDoneCard, ShapeCard, SubjectsCard, TodayCard,
} from "./AreaCards";
import { GoalSheet } from "./GoalsScreen";
import { TaskList } from "./TasksScreen";
import { AREA_MEANINGS, AREA_TABS, areaAddChoices, balanceColumns, columnPlaces } from "./areaOverview";
import { PaceCard, RepeatingCard } from "../patterns/AreaPatterns";

/**
 * An area page's cards in two columns balanced by height, starting and ending level. Each column keeps the page's
 * order, Today first on the left, and the split whose columns come closest stands (balanceColumns); each column
 * stacks its cards at their own heights, and the shorter one's last card stretches by what is left, its content at
 * its top. The cards stay in one list, ordered left column then right, so keyboard and reading order go down the
 * left, then the right, and a card changing columns is moved, not made again: it keeps what it had open, and its
 * focus is given back. The cards are measured and placed before anything is drawn, and again whenever one's size
 * changes. On a phone they make one column, in their order.
 * @param {object} props
 * @param {import("react").ReactNode} props.children - The page's cards, in order; one left out (false or null) takes no place.
 */
function AreaColumns({ children }) {
  const cards = Children.toArray(children);
  const phone = useViewport().width <= PHONE_WIDTH;
  const [sides, setSides] = useState(() => new Map());
  const grid = useRef(null);
  const latest = useRef(null);
  const observer = useRef(null);
  const watched = useRef(new Set());
  // The bottom padding added to each stretched card, so its natural height can be read back.
  const stretched = useRef(new WeakMap());
  const focused = useRef(null);
  const columnOf = new Map(cards.map((card, index) => [card.key, sides.get(card.key) ?? index % 2]));
  const ordered = phone ? cards : [0, 1].flatMap((column) => cards.filter((card) => columnOf.get(card.key) === column));

  /** Take a card's stretch away, back to its own bottom padding. */
  const unstretch = (card) => {
    if (!stretched.current.has(card)) return;
    card.style.paddingBottom = "";
    stretched.current.delete(card);
  };

  /**
   * Measure every card and place it; or, when the cards should change columns, re-order them first, at once when
   * an observer asks, so nothing is drawn between. Each card's own size is watched; a stretch is padding, which
   * that size leaves out, so placing never sets the watch off again.
   * @param {boolean} observed - Whether a change of a card's size asks, rather than a render.
   */
  const place = (observed) => {
    const box = grid.current;
    if (!box || !latest.current) return;
    const { keys, narrow, now } = latest.current;
    const slots = new Map([...box.children].map((slot) => [slot.dataset.slot, slot]));
    const shown = new Set([...slots.values()].flatMap((slot) => [...slot.children]));
    watched.current.forEach((card) => shown.has(card) || (observer.current.unobserve(card), watched.current.delete(card)));
    shown.forEach((card) => watched.current.has(card) || (observer.current.observe(card), watched.current.add(card)));
    if (narrow) {
      box.style.height = "";
      slots.forEach((slot) => { slot.style.top = ""; [...slot.children].forEach(unstretch); });
      return;
    }
    const gap = parseFloat(getComputedStyle(box).getPropertyValue("--dw-area-gap")) || 0;
    // A card's natural height: its place's, less any stretch it was given.
    const heights = keys.map((key) => [...slots.get(key).children]
      .reduce((height, card) => height - (stretched.current.get(card) || 0), slots.get(key).getBoundingClientRect().height));
    const chosen = balanceColumns(heights, gap, keys.map((key) => now.get(key)));
    if (chosen.some((side, index) => side !== now.get(keys[index]))) {
      const next = new Map(keys.map((key, index) => [key, chosen[index]]));
      if (box.contains(document.activeElement)) focused.current = document.activeElement;
      if (observed) flushSync(() => setSides(next));
      else setSides(next);
      return;
    }
    const { tops, height, stretch } = columnPlaces(heights, chosen, gap);
    box.style.height = `${height}px`;
    keys.forEach((key, index) => {
      const slot = slots.get(key);
      slot.style.top = `${tops[index]}px`;
      const card = slot.lastElementChild;
      [...slot.children].filter((child) => child !== card || stretch?.index !== index).forEach(unstretch);
      if (card && stretch?.index === index) {
        const own = parseFloat(getComputedStyle(card).paddingBottom) - (stretched.current.get(card) || 0);
        card.style.paddingBottom = `${own + stretch.by}px`;
        stretched.current.set(card, stretch.by);
      }
    });
  };

  useLayoutEffect(() => {
    observer.current = new ResizeObserver(() => latest.current?.place(true));
    watched.current.clear();
    return () => observer.current.disconnect();
  }, []);

  useLayoutEffect(() => {
    latest.current = { keys: cards.map((card) => card.key), narrow: phone, now: sides, place };
    const back = focused.current;
    focused.current = null;
    if (back?.isConnected && document.activeElement !== back) back.focus({ preventScroll: true });
    place(false);
  });

  return (
    <div ref={grid} className="dw-area-grid">
      {ordered.map((card) => (
        <div key={card.key} className="dw-area-slot" data-slot={card.key} data-side={phone ? undefined : columnOf.get(card.key)}>{card}</div>
      ))}
    </div>
  );
}

/**
 * One area of Records, in two tabs under its name and purpose. Overview is a page of cards in two columns: first the
 * day on show in the area and its agent's notes, the same in every area, then the area's own cards, each built by the
 * local service from its tasks, goals and repeats, then its repeating tasks' planned against actual, and last, in
 * Learn alone, its section pace and its Library. Tasks is every task in the area, the Tasks screen's own list with the
 * area fixed; a card's See all opens it. Reports are for today only; a past day is history. A goal's row opens its
 * Edit sheet here, a Learning goal's with its week. Everything is added from one + Add at the top, on either tab, whose
 * menu starts a task or a goal, and in Learn a note or file; no card adds anything.
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
 * @param {"overview"|"tasks"} props.tab - The tab on show, the one last chosen for this area (see areaTabOf).
 * @param {(tab: string) => void} props.onTab - Show a tab, and keep it as this area's while the app runs.
 * @param {(text?: string) => void} props.onAskAva - Open Ava, with a request typed in and not sent.
 * @param {(goalId: string|null, payload: object) => Promise<void>} props.onSaveGoal - Save a goal.
 * @param {(item: object) => void} props.onEditTask - Edit one of a goal's tasks.
 * @param {(item: object) => Promise<void>} props.onRemoveTask - Delete one of a goal's past tasks.
 * @param {object[]|null} props.library - The Library's notes and files, newest first; null until they load.
 * @param {() => void} props.onAddToLibrary - Add a note or file, from Learn's + Add.
 * @param {() => void} props.onSeeLibrary - Open the Library.
 * @param {boolean} props.sheetOpen - Whether a task's sheet, the Library's add sheet or the Guide's is on show, over a goal's.
 * @param {(screen: string) => void} props.onGuide - Open the Areas card from the Guide.
 */
export function AreaScreen({ domain, day, today, backendConnected, onRecords, onToday, onTodayScreen, onAddTask, onOpenRow, onOpenTask,
  onStatus, tab, onTab, onAskAva, onSaveGoal, onEditTask, onRemoveTask, library, onAddToLibrary, onSeeLibrary, sheetOpen, onGuide }) {
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
  // The one + Add: a task or goal in the area, or in Learn a note or file, each starting with no goal.
  const add = { task: () => onAddTask({ domain }), goal: () => setEditing({ newIn: domain }), note: () => onAddToLibrary() };
  // A card's See all {area} tasks opens the page's own Tasks tab.
  const seeAll = () => onTab("tasks");
  const own = data && ({
    learning: [<SubjectsCard key="subjects" {...shared} {...goals} onSeeAll={seeAll} />,
      <PracticeCard key="practice" {...shared} />, <PaceCard key="pace" data={data} />],
    life: [<HabitsCard key="habits" {...shared} />, <ShapeCard key="shape" data={data} day={day} today={today} onOpenTask={onOpenTask} />,
      <EnergyCard key="energy" data={data} today={today} onTodayScreen={onTodayScreen} />],
    work: [<LoadCard key="load" {...shared} />, <MeetingsCard key="meetings" {...shared} />,
      <CarryOversCard key="carry" data={data} onOpenTask={onOpenTask} onAskAva={onAskAva} onSeeAll={seeAll} />],
    project: [<ProjectsCard key="projects" {...shared} {...goals} />, <NextStepsCard key="next" {...shared} />,
      <RecentlyDoneCard key="recent" data={data} onOpenTask={onOpenTask} onSeeAll={seeAll} />],
  })[domain];
  const repeating = data && <RepeatingCard key="repeating" domain={domain} data={data} />;

  return (
    <main className="dw-page" tabIndex={-1}>
      <button type="button" className="dw-back" onClick={onRecords}><Icon name="left" size={18} />{t("navRecords")} / {t("areasHeading")}</button>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <div className="dw-title-guide">
            <h1 className="dw-display dw-area-title"><AreaGlyph domain={domain} />{t(domain)}</h1>
            <GuideButton screen={domain === "learning" ? "learning" : "areas"} onOpen={onGuide} />
          </div>
        </div>
        <div className="dw-page-actions dw-area-actions">
          <ActionMenu label={t("areaAddLabel", { area: t(domain) })} text={t("addAction")} disabled={!backendConnected}
            items={areaAddChoices(domain).map(([value, key, icon]) => ({ value, label: t(key), icon }))} onChoose={(choice) => add[choice]()} />
        </div>
      </header>
      <p className="dw-area-purpose">{t(AREA_MEANINGS[domain])}</p>
      <TabList label={t(domain)} idBase="dw-area" tabs={AREA_TABS.map(([id, key]) => [id, t(key)])} selected={tab} onSelect={onTab} />
      <div id="dw-area-panel" role="tabpanel" aria-labelledby={`dw-area-tab-${tab}`} className="dw-area-panel">
        <PageBanners day={day} backendConnected={backendConnected} />
        {!isToday && (
          <p className={`dw-banner ${past ? "dw-banner-history" : "dw-banner-caution"}`} role="note">
            <Icon name={past ? "lock" : "calendar"} size={18} />
            <span>{t(past ? "areaPastDay" : "areaFutureDay", { date: fullDate(day.date, language) })}</span>
            <button type="button" className="dw-link" onClick={onToday}>{t("showTodayAction")}</button>
          </p>
        )}
        {tab === "tasks" ? (
          <TaskList day={day} today={today} backendConnected={backendConnected} area={domain} onOpenTask={onOpenTask} />
        ) : (
          <>
            {error && <p className="dw-alert" role="alert">{error}</p>}
            {!backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("areaNeedsService")}</p>}
            <div className="dw-page-body">
              <AreaColumns>
                <TodayCard domain={domain} day={day} today={today} backendConnected={backendConnected} onOpenRow={onOpenRow}
                  onStatus={onStatus} onSeeAll={seeAll} />
                {data ? <NotesCard domain={domain} notes={data.notes} today={today} onToday={onToday} onAskAva={() => onAskAva()} />
                  : backendConnected && <p className="dw-muted">{t("loadingArea")}</p>}
                {own}
                {repeating}
                {domain === "learning" && <LibraryCard items={library} onSeeLibrary={onSeeLibrary} />}
              </AreaColumns>
              {!isToday && <p className="dw-caption dw-area-note"><AreaTag domain={domain} plain /> {t("areaReportsToday")}</p>}
            </div>
          </>
        )}
      </div>
      {editing !== undefined && (
        <GoalSheet key={editing?.id || "new"} goal={editing?.newIn ? null : editingGoal} today={today} backendConnected={backendConnected}
          hidden={sheetOpen} atTasks={false} defaultDomain={editing?.newIn || domain} library={library} onSave={onSaveGoal} onEditTask={onEditTask}
          onDeleteTask={onRemoveTask} onClose={() => setEditing(undefined)}
          week={data?.subjects?.find((subject) => subject.goalId === editingGoal?.id)} onOpenTask={onOpenTask} onAskAva={onAskAva} />
      )}
    </main>
  );
}
