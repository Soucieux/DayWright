import { useI18n } from "../i18n";
import { AreaGlyph } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { agentName } from "../ui/agentName";
import { clockOfTimestamp, formatMinutes } from "../time";
import { findingText, findingsFor } from "../plans/findings";
import { pausedInPlan } from "../plans/pausedTasks";
import { planName } from "../plans/planName";
import { planNotes } from "../plans/planNotes";
import { planChanges } from "./planChanges";

/** The findings that explain a change: a shorter block, or a time near when it's usually done. */
const RESIZE_REASONS = ["shorten", "asked-shorter"];
const PLACE_REASONS = ["time"];

/**
 * One change the set plan made to a task, with the area agents' findings behind it.
 * @param {object} props
 * @param {object} props.change - The entry, its task, and whether it was placed, moved or resized.
 * @param {object[]} props.route - The agents' runs that proposed the plan.
 */
function PlanChange({ change, route }) {
  const { t, language, demoText } = useI18n();
  const { entry, task, placed, moved, resized } = change;
  const what = [
    placed && t("changePlacedAt", { time: entry.start_time }),
    moved && t("changeMovedTo", { from: task.start_time, to: entry.start_time }),
    resized && t("changeResized", { to: formatMinutes(entry.duration_minutes, language), from: formatMinutes(task.duration_minutes, language) }),
  ].filter(Boolean).join(t("clauseSeparator"));
  const reasons = findingsFor(route, task.title, task.domain, [...(resized ? RESIZE_REASONS : []), ...(placed ? PLACE_REASONS : [])]);
  return (
    <li>
      <p className="dw-plan-change"><AreaGlyph domain={entry.domain} /><strong>{demoText(entry.title)}</strong><span>{what}</span></p>
      {reasons.map((finding) => (
        <p key={finding.kind} className="dw-plan-reason"><Icon name="agent" size={14} />
          <span>{t("agentSays", { agent: agentName(finding.agent, t), text: findingText(finding, t, language, demoText) })}</span></p>
      ))}
    </li>
  );
}

/**
 * Today's plan in one place: before one is set, how the agents made the proposals; once one is set,
 * which plan is being followed, what it changed from the tasks as recorded and why, which of its
 * tasks are paused with their goal or were left out for that, and the buttons to view the plans,
 * ask for a replacement, or deselect it.
 * @param {object} props
 * @param {object} props.day - Today's records and plans.
 * @param {boolean} props.fromPlan - Whether a plan is set.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onPlans - Open the plans.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {() => void} props.onDeselect - Stop following the set plan.
 */
export function PlanSection({ day, fromPlan, backendConnected, onPlans, onReplace, onDeselect }) {
  const { t, language, demoText } = useI18n();
  const route = day.planRoute || [];
  if (!fromPlan) {
    return (
      <section className="dw-card" aria-labelledby="dw-plan-section-title">
        <h2 id="dw-plan-section-title" className="dw-heading">
          {day.planSetId ? `${day.variants.length} ${t("draftsNotSet")}` : t("noPlanSetYet")}</h2>
        {day.planSetId && (
          <div className="dw-plan-actions">
            <button type="button" className="dw-button" onClick={onPlans}><Icon name="eye" size={18} />{t("viewPlansAction", { count: day.variants.length })}</button>
          </div>
        )}
      </section>
    );
  }
  const variant = day.variants.find((candidate) => candidate.id === day.confirmedVariantId);
  const { changed, kept, missing: notScheduled } = planChanges(day.entries, day.dayItems);
  const paused = pausedInPlan(day.entries, day.dayItems);
  const missing = notScheduled.filter((task) => !paused.left.includes(task));
  const names = (rows) => rows.map((row) => `“${demoText(row.title)}”`).join(t("listSeparator"));
  return (
    <section className="dw-card dw-plan-section" aria-labelledby="dw-plan-section-title">
      <p className="dw-eyebrow">{t("followingLabel")}</p>
      <h2 id="dw-plan-section-title" className="dw-heading">
        {planName(variant, t, demoText)}{day.confirmedAt && ` · ${t("setAtTime", { time: clockOfTimestamp(day.confirmedAt) })}`}</h2>
      {variant && <p className="dw-muted">{planNotes(variant, t, language, demoText).apart}</p>}
      <h3 className="dw-section-label">{t("planChangedHeading")}</h3>
      {changed.length > 0
        ? <ul className="dw-plan-changes">{changed.map((change) => <PlanChange key={change.entry.id} change={change} route={route} />)}</ul>
        : <p className="dw-muted">{t("planChangedNothing")}</p>}
      {kept.length > 0 && changed.length > 0 && <p className="dw-caption">{t("planKeptAsSet", { tasks: names(kept) })}</p>}
      {missing.length > 0 && <p className="dw-caption">{t("notIncluded", { items: names(missing) })}</p>}
      {paused.held.length > 0 && <p className="dw-row-note dw-row-paused-note"><Icon name="pause" size={16} />{t("planHeldPausedSet", { items: names(paused.held) })}</p>}
      {paused.left.length > 0 && <p className="dw-row-note dw-row-paused-note"><Icon name="pause" size={16} />{t("planLeftPaused", { items: names(paused.left) })}</p>}
      <div className="dw-plan-actions">
        <button type="button" className="dw-button" onClick={onPlans}><Icon name="eye" size={18} />{t("viewPlansAction", { count: day.variants.length })}</button>
        <button type="button" className="dw-button" disabled={!backendConnected} onClick={onReplace}><Icon name="history" size={18} />{t("askReplacement")}</button>
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={onDeselect}><Icon name="x" size={18} />{t("deselectPlanAction")}</button>
      </div>
    </section>
  );
}
