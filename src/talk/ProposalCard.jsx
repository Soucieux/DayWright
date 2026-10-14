import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { agentName } from "../ui/agentName";
import { planName } from "../plans/planName";
import { CatchUpList } from "../records/CatchUpList";
import { EntryFields } from "../settings/EntryFields";
import { entryLine, missingFields, neededText, shortDay } from "../settings/memory";
import { openSettings } from "../settings/models";
import { chosenStatuses, firstChoices } from "../records/catchUp";
import { formatMinutes, fullDate, shortDate } from "../time";
import { CHECK_TIMES_TITLES, cardDay, changeLine, checkedTimes, leftOutLine, newTaskLine, proposalView, shownChange } from "./proposal";

/** The icon beside each change an edit makes to a past task. */
const CHANGE_ICONS = {
  title: "pencil", detail: "pencil", domain: "target", goalId: "link", date: "calendar",
  startTime: "clock", durationMinutes: "clock", status: "check", actualTime: "clock", timeConfirmed: "check",
};

/**
 * What a confirmed meal move did to today's set plan: the tasks fitted around the meal, or, when
 * the plan is up for review, the new plans to pick from here, or to compare in Plans.
 * @param {object} props
 * @param {{planUpdate: string, changes: object[], review?: {options: object[]}}} props.outcome - The move's result.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether a plan can be set.
 * @param {(option: object) => Promise<void>} props.onPicked - Refresh after one of the new plans is set.
 * @param {() => void} props.onOpenPlans - Show today's plans.
 */
function MealOutcome({ outcome, today, backendConnected, onPicked, onOpenPlans }) {
  const { t, serviceText } = useI18n();
  const [picked, setPicked] = useState(null);
  const [error, setError] = useState("");

  /**
   * Set one of the new plans in place of today's set plan.
   * @param {{id: string, name: string, slug: string}} option - The plan picked.
   */
  async function use(option) {
    setError("");
    try {
      await api("/api/plan/confirm", { method: "POST", body: JSON.stringify({ date: today, variantId: option.id, replaceExisting: true }) });
      setPicked(option);
      await onPicked(option);
    } catch (caught) {
      setError(caught.message);
    }
  }

  if (outcome.planUpdate === "adjusted") {
    return (
      <>
        <p className="dw-caption">{t("mealAdjustedTitle")}</p>
        <ul className="dw-proposal-changes">
          {outcome.changes.map((change) => (
            <li key={change.title}><Icon name="clock" size={18} /><span>{t("proposalMoveLine", { title: change.title, from: change.from, to: change.to })}</span></li>
          ))}
        </ul>
      </>
    );
  }
  if (outcome.planUpdate !== "review") return null;
  if (picked) return <p className="dw-caption" role="status">{t("mealReviewSet", { name: planName(picked, t, serviceText) })}</p>;
  return (
    <>
      <p className="dw-caption">{t("mealReviewTitle")}</p>
      <div className="dw-actions">
        {outcome.review.options.map((option) => (
          <button key={option.id} type="button" className="dw-button" disabled={!backendConnected} onClick={() => use(option)}>
            {t("mealReviewUse", { name: planName(option, t, serviceText) })}</button>
        ))}
        <button type="button" className="dw-button dw-button-quiet" onClick={onOpenPlans}>{t("mealReviewCompare")}</button>
      </div>
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </>
  );
}

/** The verdicts a folder's check gives its files, in the order its card lists them, with their headings. */
const FOLDER_VERDICTS = [["ready", "folderCheckReady"], ["unreadable", "folderCheckUnreadable"], ["not-study", "folderCheckNotStudy"]];

/**
 * A folder check card's files under their verdicts, each with a tick box: ticked ones stay in the Library
 * on Confirm, and the rest leave it. A file that can't be read says why.
 * @param {object} props
 * @param {{path: string, title: string, verdict: string, reason: string|null}[]} props.files - The files checked.
 * @param {Set<string>} props.ticks - The paths ticked now.
 * @param {(path: string, ticked: boolean) => void} props.onTick - Tick or untick a file.
 */
function FolderCheckFiles({ files, ticks, onTick }) {
  const { t } = useI18n();
  return FOLDER_VERDICTS.filter(([verdict]) => files.some((file) => file.verdict === verdict)).map(([verdict, key]) => (
    <fieldset key={verdict} className="dw-folder-check">
      <legend className="dw-eyebrow">{t(key)}</legend>
      {files.filter((file) => file.verdict === verdict).map((file) => (
        <label key={file.path} className="dw-folder-check-file">
          <input type="checkbox" checked={ticks.has(file.path)} onChange={(event) => onTick(file.path, event.target.checked)} />
          <span>{file.title}<span className="dw-caption"> · {file.reason || file.path}</span></span>
        </label>
      ))}
    </fieldset>
  ));
}

/**
 * A check-times card's times: each task's kept time and set length, with its day on a card that checks more
 * than one day's, Right or Change, and for a change the minutes it took. A task that needs a status before its
 * time can be checked says so instead, with Catch up on its day.
 * @param {object} props
 * @param {{itemId: string, date?: string, title: string, start: string|null, end: string|null, minutes: number|null,
 *   setMinutes: number, needsStatus?: boolean}[]} props.tasks - The times to check.
 * @param {boolean} [props.dated=false] - Whether the card checks more than one day's times, so each row names its day.
 * @param {Record<string, {choice?: string, minutes?: string}>} props.checks - What the user chose for each.
 * @param {(itemId: string, check: object) => void} props.onCheck - Change one task's choice.
 * @param {(date: string) => void} [props.onCatchUp] - Ask Ava to catch up on a day.
 */
function CheckTimesList({ tasks, dated = false, checks, onCheck, onCatchUp }) {
  const { t, language } = useI18n();
  return (
    <ul className="dw-check-times">
      {tasks.map((task) => {
        const check = checks[task.itemId] || {};
        const title = task.title;
        if (task.needsStatus) {
          return (
            <li key={task.itemId}>
              <div className="dw-check-times-task">
                <span className="dw-check-times-title">{title}</span>
                <span className="dw-caption">{dated ? `${shortDate(task.date, language)} · ` : ""}{t("checkTimeNeedsStatus")}</span>
              </div>
              {onCatchUp && (
                <button type="button" className="dw-button dw-button-quiet dw-check-times-catch-up"
                  aria-label={t("checkTimeCatchUpFor", { title })} onClick={() => onCatchUp(task.date)}>{t("catchUpAction")}</button>
              )}
            </li>
          );
        }
        return (
          <li key={task.itemId}>
            <div className="dw-check-times-task">
              <span className="dw-check-times-title">{title}</span>
              <span className="dw-caption">{dated ? `${shortDate(task.date, language)} · ` : ""}{t("checkTimeLine", { start: task.start,
                end: task.end, minutes: formatMinutes(task.minutes, language), set: formatMinutes(task.setMinutes, language) })}</span>
            </div>
            <Segmented label={t("checkTimeFor", { title })} value={check.choice || ""} onChange={(choice) => onCheck(task.itemId, { ...check, choice })}
              options={[["right", t("checkTimeRight")], ["change", t("checkTimeChange")]]} />
            {check.choice === "change" && (
              <label className="dw-field dw-check-times-minutes"><span className="dw-field-label">{t("checkTimeMinutes")}</span>
                <input type="number" min="1" max="1440" inputMode="numeric" value={check.minutes || ""}
                  onChange={(event) => onCheck(task.itemId, { ...check, minutes: event.target.value })} /></label>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * A change the agents proposed, pencilled until the user confirms or dismisses it. It lists exactly
 * what would change and what stays as it is; nothing is applied until Confirm.
 * @param {object} props
 * @param {object} props.proposal - The proposed change.
 * @param {object} props.day - The day on show, for its plans and tasks.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the change can be applied.
 * @param {(payload: object, actionType: string) => Promise<void>} props.onConfirmed - Refresh after the
 *   change is applied, given what it changed and its kind.
 * @param {() => void} props.onOpenPlans - Show today's plans, to compare them after a meal move.
 * @param {(date: string) => void} [props.onCatchUp] - Ask Ava to catch up on a day, for a check-times card's task
 *   that needs a status first.
 */
/** A memory card's last line, saying where what Ava remembers is edited or deleted, with Settings › Memory a link there. */
function MemorySettingsLine() {
  const { t } = useI18n();
  const [before, after] = t("proposalRememberSettings").split("{place}");
  return (
    <>{before}<button type="button" className="dw-link" onClick={() => openSettings("memory")}>{t("settingsMemoryPlace")}</button>{after}</>
  );
}

export function ProposalCard({ proposal, day, today, backendConnected, onConfirmed, onOpenPlans, onCatchUp }) {
  const { t, language, serviceText } = useI18n();
  const [decision, setDecision] = useState("");
  const [outcome, setOutcome] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // A new task without a goal, or a new goal, goes in the area the Orchestrator suggested until the user picks another.
  const [area, setArea] = useState(proposal.payload?.domain);
  // A catch-up card's choice for each task, as Ava read it until the user changes it.
  const [choices, setChoices] = useState(() => (proposal.actionType === "catch_up" ? firstChoices(proposal.payload.tasks) : {}));
  // A folder check card's files to keep, those ready to study until the user ticks or unticks any.
  const [ticks, setTicks] = useState(() => new Set(proposal.actionType === "folder_check"
    ? proposal.payload.files.filter((file) => file.ticked).map((file) => file.path) : []));
  // A check-times card's choice for each time, none until the user makes one.
  const [checks, setChecks] = useState({});
  // A card to remember a rule its words didn't fill: whether the user makes it a rule, and the rule as they fill it.
  const [asRule, setAsRule] = useState(false);
  const [rule, setRule] = useState(() => (proposal.actionType === "remember" && proposal.payload.rule
    ? { ...proposal.payload.entry, ...proposal.payload.ruleFields, kind: "rule", ruleKind: proposal.payload.rule } : null));
  // A card of things to remember: the places of those still ticked, every one until the user unticks any.
  const [kept, setKept] = useState(() => new Set(proposal.actionType === "review_memory" ? proposal.payload.entries.keys() : []));
  const statusRef = useRef(null);
  const view = proposalView(proposal, day.dayItems || []);
  const line = (entry) => entryLine(entry, t, language);
  const choosesArea = view.kind === "addGoal" || (view.kind === "addTask" && !view.goalTitle);
  const catchingUp = view.kind === "catchUp";
  // A title reads "today" or "tomorrow" as words, any other day as "on Fri 9 Oct".
  const named = (date) => (date ? cardDay(date, today, t, language) : { on: "", plain: "" });
  const { on: when, plain: whenAlone } = named(view.date);
  const plan = (id, name) => planName((day.variants || []).find((variant) => variant.id === id), t, serviceText) || serviceText(name);
  const dayList = (dates) => dates.map((date) => named(date).plain).join(language === "zh" ? "、" : ", ");

  const [title, changes] = view.kind === "set" ? [t("proposalSetTitle", { date: whenAlone }), [
    ["check", t("proposalSetLine", { name: plan(proposal.payload.variantId, view.to) })],
    ["target", t("goalsOnlyOnReport")],
  ]] : view.kind === "replace" ? [t("proposalReplaceTitle", { date: whenAlone }), [
    ["repeat", t("proposalReplaceLine", { from: plan(proposal.payload.reviewedFromVariantId, view.from), to: plan(proposal.payload.variantId, view.to) })],
    ["lock", t("reportedKeepStatus")],
    ["target", t("goalsOnlyOnReport")],
  ]] : view.kind === "shorten" ? [t("proposalShortenTitle", { when }), [
    ["clock", view.title
      ? t("proposalShortenLine", { title: view.title, from: formatMinutes(view.from, language), to: formatMinutes(view.to, language) })
      : t("proposalShortenTo", { to: formatMinutes(view.to, language) })],
    ["calendar", t("proposalStaysOnCalendar")],
  ]] : view.kind === "move" ? [t("proposalMoveTitle", { when }), [
    ["clock", view.title
      ? t("proposalMoveLine", { title: view.title, from: view.from || t("untimed"), to: view.to })
      : t("proposalMoveTo", { to: view.to })],
    ["pin", t("proposalMoveFixed")],
  ]] : view.kind === "length" ? [t("proposalShortenTitle", { when }), [
    ["clock", view.title
      ? t("proposalShortenLine", { title: `“${view.title}”`, from: formatMinutes(view.from, language), to: formatMinutes(view.to, language) })
      : t("proposalLengthTo", { to: formatMinutes(view.to, language) })],
    ["shield", t("proposalLengthYours")],
  ]] : view.kind === "usual" ? [t("proposalUsualTitle", { title: view.title }), [
    ["clock", t("proposalUsualLine", { from: formatMinutes(view.from, language), to: formatMinutes(view.to, language) })],
    ["calendar", view.days === 1 ? t("proposalUsualDay", { date: named(view.date).plain })
      : t("proposalUsualDays", { count: view.days, date: named(view.date).plain })],
    ["shield", t("proposalLengthYours")],
  ]] : view.kind === "edit" ? [t("proposalEditTitle", { title: view.title, when }), [
    // A past task still without a status reads Not done · no reply, or · paused, so its change says so.
    ...view.changes.map((change) => [CHANGE_ICONS[change.field], changeLine(shownChange(change, view, today),
      t, language, day.goals || [])]),
    ...(view.days ? [["calendar", view.days.length === 1 ? t("proposalDayChanges", { day: named(view.days[0]).plain })
      : t("proposalDaysChange", { count: view.days.length, days: dayList(view.days) })]] : []),
    ...(view.leftOut ? [["lock", leftOutLine(view.leftOut, t, language)]] : []),
    ["lock", t("proposalEditNote")],
  ]] : view.kind === "repeat" ? [t("proposalRepeatTitle", { title: view.title }), [
    ["repeat", view.mode === "stop" ? t("proposalRepeatStops", { day: named(view.startsOn).plain })
      : t("proposalRepeatFrom", { kind: t(view.repeatKind === "weekly" ? "repeatWeekly" : "repeatDaily"),
        day: named(view.startsOn).plain })],
    ...(view.removes.length ? [["trash", t("proposalRepeatRemoves", { days: dayList(view.removes) })]] : []),
  ]] : view.kind === "meal" ? [t(view.scope === "standing" ? "proposalMealStandingTitle" : "proposalMealDayTitle",
    { meal: t(`meal${view.title}`), date: whenAlone, when }), [
    ["meal", t("proposalMealLine", { meal: t(`mealName${view.title}`), from: view.from, to: view.to })],
    ...(view.replaces.length ? [["repeat", t("proposalMealReplaces", { meal: t(`meal${view.title}`), days: view.replaces
      .map(({ date, range }) => (language === "zh" ? `${fullDate(date, language)}（${range}）` : `${fullDate(date, language)} (${range})`))
      .join(language === "zh" ? "、" : ", ") })]] : []),
    ["calendar", t(view.planChanges ? "proposalMealPlanChanges" : "proposalMealKeepsFree")],
  ]] : view.kind === "addTask" ? [t("proposalAddTaskTitle", { when }), [
    ["plus", newTaskLine(view.task, today, t, language)],
    ...(view.continues ? [["repeat", t("proposalContinueLine", { title: view.task.title, date: named(view.continues.date).plain,
      count: view.continues.left.length, items: view.continues.left.join(language === "zh" ? "、" : ", ") })]] : []),
    ...(view.goalTitle ? [["link", t("proposalJoinsGoal", { goal: view.goalTitle })]] : []),
    ["shield", t("proposalAddChecked")],
  ]] : view.kind === "link" ? [t(view.link ? "proposalLinkTitle" : "proposalUnlinkTitle", { title: view.title }), [
    ...view.sources.map((entry) => ["book", t(view.link ? "proposalLinkLine" : "proposalUnlinkLine", { name: entry.title })]),
    ...(view.suggested ? [["agent", t("proposalLinkSuggested", { agent: agentName("learning", t) })]] : []),
    ["lock", t(view.link ? "proposalLinkNote" : "proposalUnlinkNote")],
  ]] : view.kind === "folderCheck" ? [t("proposalFolderCheckTitle", { title: view.title }), [
    ["check", t("proposalFolderCheckCounts", Object.fromEntries([["ready", "ready"], ["unreadable", "unreadable"], ["notStudy", "not-study"]]
      .map(([name, verdict]) => [name, view.files.filter((file) => file.verdict === verdict).length])))],
    ...(view.modelChecked ? [] : [["info", t("proposalFolderCheckNoModel")]]),
    ["lock", t("proposalFolderCheckNote")],
  ]] : view.kind === "pause" ? [t("proposalPauseTitle"), [
    ["pause", t("proposalPauseLine")],
    ["lock", t("proposalPauseNote")],
  ]] : view.kind === "resume" ? [t("proposalResumeTitle"), [
    ["arrow", t("proposalResumeLine", { since: view.since })],
  ]] : view.kind === "checkTimes" ? [view.date ? t("proposalCheckTimesTitle", { when }) : t(CHECK_TIMES_TITLES[view.period] || "proposalCheckTimesAllTitle"), [
    ["lock", t("proposalCheckTimesNote")],
  ]] : view.kind === "catchUp" ? [t("proposalCatchUpTitle", { when }), [
    ["lock", t("proposalCatchUpNote")],
  ]] : view.kind === "tick" ? [t("proposalTickTitle", { when }), [
    ["check", t(view.done ? "proposalTick" : "proposalUntick", { item: view.item, title: view.title })],
  ]] : view.kind === "addGoal" ? [t("proposalAddGoalTitle", { title: view.title }), [
    ...view.tasks.map((task) => ["plus", newTaskLine(task, today, t, language)]),
    ...(view.tasks.length ? [["shield", t("proposalAddChecked")]] : []),
  ]] : view.kind === "energy" ? [t("proposalEnergyTitle"), [
    ["plus", t("proposalEnergyReading", { level: view.level })],
    ["sparkline", view.before == null ? t("proposalEnergyAverageNew", { after: view.after })
      : t("proposalEnergyAverage", { before: view.before, after: view.after })],
    ["calendar", t("proposalEnergyToday")],
  ]] : view.kind === "remove" ? [t("proposalRemoveTitle", { when }), [
    ["trash", t("proposalRemoveLine", { title: view.title, when: view.start || t("untimed"),
      length: formatMinutes(view.minutes, language) })],
    ...(view.keptByPlan ? [["calendar", t("proposalRemoveKeptEntry")]] : []),
    ["lock", t("proposalRemoveNote")],
  ]] : view.kind === "remember" ? [t(view.outcome === "update" ? "proposalMemoryChangeTitle"
    : view.offered ? "proposalRememberOfferTitle" : "proposalRememberTitle"), [
    ["agent", t("proposalRememberAva", { agent: t("navTalk") })],
    view.outcome === "update" ? ["repeat", `${line(view.before)} → ${line(asRule && rule ? rule : view.entry)}`]
      : ["pin", line(asRule && rule ? rule : view.entry)],
    ...(view.missing.length && !asRule ? [["info", t("proposalRememberAsNote", { fields: neededText(view.missing, t, language) })]] : []),
    ["lock", <MemorySettingsLine key="memory" />],
  ]] : view.kind === "memoryChange" ? [t("proposalMemoryChangeTitle"), [
    ...view.changes.map((change) => (change.op === "update" ? ["repeat", `${line(change.before)} → ${line(change.after)}`]
      : change.op === "end" ? ["clock", t("proposalMemoryEnd", { line: line(change.before) })]
        : ["trash", t("proposalMemoryDelete", { line: line(change.before) })])),
    ["lock", <MemorySettingsLine key="memory" />],
  ]] : view.kind === "memoryForget" ? [t("proposalForgetTitle", { subject: view.topic }), [
    ...view.entries.map((entry) => ["trash", line(entry)]),
    ...view.lines.map((said) => ["trash", t("proposalForgetLine", { date: shortDay(said.day, language), text: said.text })]),
    ["lock", t("proposalForgetNote")],
  ]] : view.kind === "memoryReview" ? [t("proposalMemoryReviewTitle"), [
    ["lock", t("proposalMemoryReviewNote")],
  ]] : [t("proposalOtherTitle"), [["info", serviceText(proposal.explanation)]]];
  // A rule the user is filling in counts only once every field it needs is there.
  const ruleUnfinished = asRule && Boolean(rule && missingFields(rule).length);

  // The button that decided is gone once the card becomes its outcome; keep focus on that outcome.
  useEffect(() => {
    if (decision) statusRef.current?.focus();
  }, [decision]);

  /**
   * Confirm or dismiss the proposal. Only a confirmation changes anything.
   * @param {string} choice - `confirmed` or `dismissed`.
   */
  async function decide(choice) {
    setBusy(true);
    setError("");
    try {
      const decided = await api(`/api/actions/${encodeURIComponent(proposal.id)}`, { method: "POST",
        body: JSON.stringify({ decision: choice, ...(choosesArea ? { domain: area } : {}),
          ...(catchingUp ? { statuses: chosenStatuses(view.tasks, choices) } : {}),
          ...(view.kind === "folderCheck" ? { ticked: [...ticks] } : {}),
          ...(view.kind === "checkTimes" ? { times: checkedTimes(view.tasks, checks) } : {}),
          ...(view.kind === "remember" && asRule && rule ? { memory: rule } : {}),
          ...(view.kind === "memoryReview" ? { kept: [...kept] } : {}) }) });
      setOutcome(decided);
      setDecision(choice);
      if (choice === "confirmed") await onConfirmed(proposal.payload, proposal.actionType);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  if (decision) {
    const status = <p className="dw-talk-decided" role="status" tabIndex={-1} ref={statusRef}><Icon name={decision === "confirmed" ? "check" : "x"} size={16} />{t(decision === "confirmed" ? "proposalConfirmed" : "proposalDismissed")}</p>;
    if (decision !== "confirmed" || !outcome?.planUpdate) return status;
    return (
      <div className="dw-meal-outcome">
        {status}
        <MealOutcome outcome={outcome} today={today} backendConnected={backendConnected} onOpenPlans={onOpenPlans}
          onPicked={(option) => onConfirmed({ date: today, variantId: option.id }, "select_variant")} />
      </div>
    );
  }
  return (
    <section className="dw-card dw-pencilled dw-proposal" aria-labelledby={`dw-proposal-${proposal.id}`}>
      <span className="dw-chip dw-chip-small dw-chip-dashed"><Icon name="pencil" size={14} />{t("proposedNotApplied")}</span>
      <h4 id={`dw-proposal-${proposal.id}`} className="dw-heading">{title}</h4>
      {catchingUp && <CatchUpList tasks={view.tasks} choices={choices}
        onChoose={(id, choice) => setChoices((now) => ({ ...now, [id]: choice }))} />}
      {view.kind === "folderCheck" && <FolderCheckFiles files={view.files} ticks={ticks}
        onTick={(path, ticked) => setTicks((now) => { const next = new Set(now); if (ticked) next.add(path); else next.delete(path); return next; })} />}
      {view.kind === "checkTimes" && <CheckTimesList tasks={view.tasks} dated={!view.date} checks={checks} onCatchUp={onCatchUp}
        onCheck={(itemId, check) => setChecks((now) => ({ ...now, [itemId]: check }))} />}
      {view.kind === "memoryReview" && (
        <fieldset className="dw-folder-check">
          <legend className="dw-visually-hidden">{t("proposalMemoryReviewTitle")}</legend>
          {view.entries.map((offer, place) => (
            <label key={place} className="dw-folder-check-file">
              <input type="checkbox" checked={kept.has(place)} onChange={(event) => setKept((now) => {
                const next = new Set(now);
                if (event.target.checked) next.add(place); else next.delete(place);
                return next;
              })} />
              <span>{line(offer.entry)}<span className="dw-caption"> · {t("memorySaid", { date: shortDay(offer.day, language) })}</span></span>
            </label>
          ))}
        </fieldset>
      )}
      <ul className="dw-proposal-changes">
        {changes.map(([icon, text], index) => <li key={index}><Icon name={icon} size={18} /><span>{text}</span></li>)}
      </ul>
      {view.kind === "remember" && rule && (
        <div className="dw-proposal-rule">
          <button type="button" className="dw-button dw-button-quiet" aria-pressed={asRule} onClick={() => setAsRule((now) => !now)}>
            {t(asRule ? "proposalKeepNote" : "proposalMakeRule")}</button>
          {asRule && <EntryFields entry={rule} onChange={setRule} />}
          {ruleUnfinished && <p className="dw-caption">{t("proposalRuleNeeds", { fields: neededText(missingFields(rule), t, language) })}</p>}
        </div>
      )}
      {view.kind === "folderCheck" && !view.modelChecked && (
        <p className="dw-caption"><button type="button" className="dw-link" onClick={() => openSettings()}>{t("openSettings")}</button></p>
      )}
      {choosesArea && (
        <div className="dw-field dw-proposal-area"><span className="dw-field-label">{t("fieldArea")}</span>
          <Segmented label={t("fieldArea")} value={area} onChange={setArea}
            options={DOMAINS.map((domain) => [domain, <AreaTag key={domain} domain={domain} plain />])} />
          {["model", "keywords"].includes(view.domainSource) && area === view.domain && (
            <p className="dw-caption"><Icon name="agent" size={16} /> {t(view.kind === "addGoal" ? "proposalGoalAreaSuggested" : "areaSuggested",
              { agent: agentName("orchestrator", t), area: t(view.domain) })}</p>
          )}
        </div>
      )}
      <p className="dw-caption">{t("nothingChangedYet")}</p>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-primary" onClick={() => decide("confirmed")}
          disabled={!backendConnected || busy || (catchingUp && !Object.keys(chosenStatuses(view.tasks, choices)).length)
            || (view.kind === "checkTimes" && !Object.keys(checkedTimes(view.tasks, checks)).length) || ruleUnfinished}>
          <Icon name="check" size={18} />{t("confirmChange")}</button>
        <button type="button" className="dw-button" disabled={!backendConnected || busy} onClick={() => decide("dismissed")}>{t("dismissAction")}</button>
      </div>
    </section>
  );
}
