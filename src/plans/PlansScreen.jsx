import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { getDay } from "../api";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { SideTabs } from "../ui/SideTabs";
import { StatusControl } from "../ui/StatusControl";
import { TimeColumn } from "../ui/TimeColumn";
import { agentName } from "../ui/agentName";
import { clockOfTimestamp, formatMinutes, fullDate } from "../time";
import { countedEntries, historyMark } from "../calendar/dayState";
import { AgentFindings } from "./AgentFindings";
import { pausedInPlan } from "./pausedTasks";
import { planGlance } from "./planGlance";
import { planName, planTagline } from "./planName";
import { planNotes } from "./planNotes";
import { PlanTypes } from "./PlanTypes";
import { ReplaceReview } from "./ReplaceReview";

/** Below this page width, padding included, the plans are compared one at a time instead of side by side. */
const ONE_AT_A_TIME_WIDTH = 900;


/**
 * Track whether the page is too narrow to show the plans side by side. The page, not the window,
 * decides, so an open sheet counts too. It measures once on opening, so a phone never
 * shows the side-by-side layout first.
 * @param {{current: HTMLElement|null}} ref - The page element.
 * @returns {boolean} True when plans should be shown one at a time.
 */
function useOneAtATime(ref) {
  const [narrow, setNarrow] = useState(false);
  useLayoutEffect(() => {
    const page = ref.current;
    const measure = () => setNarrow(page.clientWidth < ONE_AT_A_TIME_WIDTH);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(page);
    return () => observer.disconnect();
  }, [ref]);
  return narrow;
}

/**
 * Load each proposed plan's own schedule, so the plans can be compared side by side. Without the
 * local service only the plan already held in memory is available.
 * @param {object} day - The day on show.
 * @param {boolean} backendConnected - Whether the local service answered.
 * @returns {{details: Object<string, object>, error: string}} Each plan's day, by plan id, and any
 *   loading failure.
 */
function usePlanDetails(day, backendConnected) {
  const [details, setDetails] = useState({});
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    if (!backendConnected || !day.planSetId) {
      setDetails(day.selectedVariantId ? { [day.selectedVariantId]: day } : {});
      return undefined;
    }
    let live = true;
    Promise.all(day.variants.map((variant) => getDay(day.date, variant.id)))
      .then((loaded) => live && setDetails(Object.fromEntries(loaded.map((result) => [result.selectedVariantId, result]))))
      .catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [day, backendConnected]);
  return { details, error };
}

/**
 * One proposed plan: what kind of plan it is in one line, the facts that tell it from the others
 * (its first task, when it ends, and the lengths it changed), why it was suggested and what sets
 * it apart, time by area, its schedule with lunch and dinner, and what it kept or left out. A task
 * paused with its goal is marked Paused wherever the plan still holds it, and named when the plan
 * left it out for that reason. Drafts are pencilled; the set plan is solid; a past day's plans are
 * history.
 * @param {object} props
 * @param {object} props.variant - The plan.
 * @param {object|undefined} props.detail - Its day as loaded, with its entries.
 * @param {object[]} props.dayItems - The day's tasks, for what the plan left out and which are paused.
 * @param {boolean} props.isSet - Whether it is the day's set plan.
 * @param {boolean} props.isChosen - Whether it is chosen and waiting to be set.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {boolean} props.showFoot - Whether to show its choose action.
 * @param {string} props.setAt - When the set plan was set, as HH:MM.
 * @param {() => void} props.onChoose - Choose this plan.
 */
function PlanColumn({ variant, detail, dayItems, isSet, isChosen, past, showFoot, setAt, onChoose }) {
  const { t, language, demoText } = useI18n();
  const name = planName(variant, t, demoText);
  const entries = detail?.entries || [];
  // Time by area leaves out a past plan's entries for tasks removed or moved away, which stay listed.
  const minutesIn = (domain) => countedEntries(entries).filter((entry) => entry.domain === domain)
    .reduce((total, entry) => total + entry.duration_minutes, 0);
  const fixed = entries.filter((entry) => entry.constraint_kind === "fixed");
  const scheduled = new Set(entries.map((entry) => entry.source_item_id));
  // A past day is history; on any other, a plan names its tasks that are paused with their goal.
  const paused = past ? { held: [], left: [] } : pausedInPlan(entries, dayItems);
  // A past day that ended paused reads its entries left without a status as Not done · paused.
  const endedPaused = dayItems.some((item) => item.dayPaused);
  const heldIds = new Set(paused.held.map((entry) => entry.id));
  const left = dayItems.filter((item) => !scheduled.has(item.id) && !paused.left.includes(item));
  const titles = (list) => [...new Set(list.map((entry) => `“${demoText(entry.title)}”`))].join(t("listSeparator"));
  const glance = planGlance(entries, dayItems);
  const { why, apart, byAgent } = planNotes(variant, t, language, demoText);
  const meals = (variant.meals || []).map((meal) => ({ ...meal, id: `meal-${meal.title}`, kind: "meal" }));
  const schedule = [...entries, ...meals].sort((first, second) => first.start_time.localeCompare(second.start_time));
  const state = past ? "history" : isChosen ? "chosen" : isSet ? "set" : "draft";
  return (
    <article className={`dw-plan dw-plan-${state}`} aria-labelledby={`dw-plan-${variant.id}`}>
      <header className="dw-plan-head">
        <h2 id={`dw-plan-${variant.id}`} className="dw-plan-name">
          {!past && <span className={`dw-radio${isChosen || isSet ? " dw-radio-on" : ""}`} aria-hidden="true" />}{name}
        </h2>
        {isSet ? <span className="dw-chip dw-chip-ink dw-chip-small"><Icon name={past ? "lock" : "check"} size={14} />{t("setChip")}</span>
          : isChosen ? <span className="dw-chip dw-chip-ink dw-chip-small"><Icon name="check" size={14} />{t("chosenChip")}</span>
            : <span className="dw-chip dw-chip-dashed dw-chip-small"><Icon name="pencil" size={14} />{t("draftChip")}</span>}
      </header>
      {planTagline(variant.slug, t) && <p className="dw-plan-intent">{planTagline(variant.slug, t)}</p>}
      {!detail ? <p className="dw-muted">{t("loadingPlans")}</p> : (
        <>
          <dl className="dw-plan-glance">
            <div><dt>{t("glanceStartsWith")}</dt><dd>{glance.first
              ? <span className="dw-glance-item">“{demoText(glance.first.title)}”<span className="dw-glance-detail">{glance.first.start}</span></span>
              : t("glanceNoTasks")}</dd></div>
            <div><dt>{t("glanceDoneBy")}</dt><dd>{glance.doneBy || "—"}</dd></div>
            <div><dt>{t("glanceLengths")}</dt><dd>{glance.resized.length
              ? glance.resized.map(({ title, from, to }) => (
                <span key={title} className="dw-glance-item">“{demoText(title)}”
                  <span className="dw-glance-detail">{t("glanceLengthChange", { from: formatMinutes(from, language), to: formatMinutes(to, language) })}</span></span>
              ))
              : t("glanceAsRecorded")}</dd></div>
          </dl>
          {why && (byAgent
            ? <p className="dw-caption dw-plan-why dw-plan-why-agent"><Icon name="agent" size={16} />
              <span>{t("planAgentReason", { agent: agentName("orchestrator", t), reason: why })}</span></p>
            : <p className="dw-caption dw-plan-why">{why}</p>)}
          {apart && (
            <div className="dw-plan-apart">
              <p className="dw-plan-apart-label">{t("planApartLabel")}</p>
              <p>{apart}</p>
            </div>
          )}
          <section className="dw-plan-section">
            <h3 className="dw-section-label">{t("timeByArea")}</h3>
            <div className="dw-stack" aria-hidden="true">
              {DOMAINS.filter((domain) => minutesIn(domain)).map((domain) => (
                <span key={domain} className={`dw-area-${areaOf(domain)}`} style={{ flexGrow: minutesIn(domain) }} />
              ))}
            </div>
            <ul className="dw-plan-legend">
              {DOMAINS.map((domain) => <li key={domain}><AreaTag domain={domain} plain /><span>{formatMinutes(minutesIn(domain), language)}</span></li>)}
            </ul>
          </section>
          <section className="dw-plan-section">
            <h3 className="dw-section-label">{t("scheduleTitle")}</h3>
            <ol className="dw-plan-schedule">
              {schedule.map((entry) => entry.kind === "meal" ? (
                <li key={entry.id} className="dw-plan-meal">
                  <TimeColumn row={entry} />
                  <Icon name="meal" size={16} />
                  <span className="dw-plan-title">{t(`mealName${entry.title}`)}</span>
                </li>
              ) : (
                <li key={entry.id} className={heldIds.has(entry.id) ? "dw-plan-paused" : undefined}>
                  <TimeColumn row={entry} />
                  <AreaGlyph domain={entry.domain} />
                  <span className="dw-plan-title">{demoText(entry.title)}</span>
                  <span className="dw-plan-flags">
                    {entry.constraint_kind === "fixed" && <Icon name="pin" size={16} label={t("flagFixed")} />}
                    {heldIds.has(entry.id) && <StatusControl paused />}
                    {entry.removed && <span className="dw-chip dw-chip-small dw-chip-history">{historyMark(entry, t, language)}</span>}
                    {past && isSet && <StatusControl readOnly value={entry.completion_status}
                      noReply={entry.completion_status === "planned" && (endedPaused ? "dayPaused" : "noReply")} />}
                  </span>
                </li>
              ))}
            </ol>
          </section>
          <section className="dw-plan-section">
            <h3 className="dw-section-label">{t("constraintsHeading")}</h3>
            <ul className="dw-plan-constraints">
              {fixed.length > 0 && <li><Icon name="pin" size={16} /><span>{t("keptFixed", { items: titles(fixed) })}</span></li>}
              {left.length > 0 && <li><Icon name="alert" size={16} /><span>{t("notIncluded", { items: titles(left) })}</span></li>}
              {paused.held.length > 0 && <li className="dw-plan-paused"><Icon name="pause" size={16} />
                <span>{t(isSet ? "planHeldPausedSet" : "planHeldPausedDraft", { items: titles(paused.held) })}</span></li>}
              {paused.left.length > 0 && <li className="dw-plan-paused"><Icon name="pause" size={16} />
                <span>{t("planLeftPaused", { items: titles(paused.left) })}</span></li>}
              {!fixed.length && !left.length && !paused.held.length && !paused.left.length
                && <li className="dw-muted">{t("noConstraints")}</li>}
            </ul>
          </section>
        </>
      )}
      {showFoot && (
        <div className="dw-plan-foot">
          {isSet ? <p className="dw-plan-set-note"><Icon name="lock" size={16} />{t("setAtTime", { time: setAt })}</p>
            : isChosen ? <p className="dw-plan-chosen-note"><Icon name="check" size={18} />{t("chosenReviewBelow")}</p>
              : <button type="button" className="dw-button dw-plan-choose" onClick={onChoose}>{t("chooseName", { name })}</button>}
        </div>
      )}
    </article>
  );
}

/**
 * The confirmation that sets a plan. Choosing a plan never sets it; this bar says what setting
 * will do and waits for the user.
 * @param {object} props
 * @param {string} props.question - Which plan, for which day.
 * @param {number} props.count - How many entries it schedules.
 * @param {string} props.name - The plan's name.
 * @param {boolean} props.narrow - Whether plans are shown one at a time.
 * @param {boolean} props.backendConnected - Whether setting can be saved.
 * @param {() => void} props.onKeep - Go back to comparing.
 * @param {() => void} props.onSet - Set the plan.
 */
function SetBar({ question, count, name, narrow, backendConnected, onKeep, onSet }) {
  const { t } = useI18n();
  return (
    <div className={`dw-setbar${narrow ? " dw-setbar-narrow" : ""}`}>
      {!narrow && <span className="dw-setbar-mark"><Icon name="check" size={20} /></span>}
      <div className="dw-setbar-text">
        <p className="dw-setbar-title">{question}</p>
        <p>{t("setConsequence", { count })}</p>
        {!backendConnected && <p id="dw-set-reason">{t("previewCannotSave")}</p>}
      </div>
      <div className="dw-setbar-actions">
        {!narrow && <button type="button" className="dw-button dw-button-on-ink" onClick={onKeep}>{t("keepComparing")}</button>}
        <button type="button" className={`dw-button${narrow ? " dw-button-primary" : ""}`} disabled={!backendConnected} aria-describedby={backendConnected ? undefined : "dw-set-reason"} onClick={onSet}>
          <Icon name="check" size={18} />{t("setName", { name })}
        </button>
      </div>
    </div>
  );
}

/**
 * Compare the day's proposed plans and set one, or review a replacement for the plan already set.
 * Side by side on wide pages, one at a time on narrow ones. A past day's plans are history.
 * @param {object} props
 * @param {object} props.day - The day whose plans are shown.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {string} props.backLabel - Names the place the back link returns to.
 * @param {() => void} props.onBack - Leave the plans.
 * @param {() => void} props.onAskDifferent - Ask the agents for different plans.
 * @param {boolean} props.proposing - Whether the agents are proposing plans now.
 * @param {() => void} props.onPropose - Ask the agents to propose plans for a day without any.
 * @param {() => void} props.onProposeAgain - Propose again the plans not set, keeping a set plan.
 * @param {(variantId: string, replaceExisting: boolean) => void} props.onSet - Set a plan.
 * @param {(screen: string) => void} props.onGuide - Open the Plans card from the Guide.
 */
export function PlansScreen({ day, today, backendConnected, proposing, backLabel, onBack, onAskDifferent, onPropose, onProposeAgain, onSet, onGuide }) {
  const { t, language, demoText } = useI18n();
  const pageRef = useRef(null);
  const narrow = useOneAtATime(pageRef);
  const { details, error } = usePlanDetails(day, backendConnected);
  const variants = day.variants;
  const setId = day.confirmedVariantId;
  const [chosenId, setChosenId] = useState(null);
  const [reviewId, setReviewId] = useState(null);
  const [shownId, setShownId] = useState(setId || variants[0]?.id || null);
  const past = day.date < today;
  const dateLabel = fullDate(day.date, language);
  const setAt = clockOfTimestamp(day.confirmedAt);
  const setVariant = variants.find((variant) => variant.id === setId);
  const shown = variants.find((variant) => variant.id === shownId) || variants[0];
  const chosen = variants.find((variant) => variant.id === chosenId);
  const candidate = past || setId ? null : narrow ? shown : chosen;
  const review = variants.find((variant) => variant.id === reviewId);
  const nameOf = (variant) => planName(variant, t, demoText);

  function choose(variant) {
    if (setId) setReviewId(variant.id);
    else setChosenId(variant.id);
  }

  function step(offset) {
    const index = variants.indexOf(shown) + offset;
    if (variants[index]) setShownId(variants[index].id);
  }

  if (review && setVariant) {
    return (
      <main className="dw-page" tabIndex={-1} ref={pageRef}>
        <ReplaceReview day={day} current={setVariant} currentEntries={details[setId]?.entries || null}
          replacement={review} replacementEntries={details[review.id]?.entries || null} setAt={setAt}
          heading={day.date === today ? t("reviewReplacementToday") : t("reviewReplacementDay", { date: dateLabel })}
          backLabel={t("plansFor", { date: dateLabel })} backendConnected={backendConnected}
          onReplace={() => onSet(review.id, true)} onKeep={() => setReviewId(null)} />
      </main>
    );
  }

  const back = <button type="button" className="dw-back" onClick={onBack}><Icon name="left" size={18} />{backLabel}</button>;

  if (!day.planSetId) {
    const needsTask = !day.dayItems.length;
    return (
      <main className="dw-page" tabIndex={-1} ref={pageRef}>
        {back}
        <div className="dw-title-guide">
          <h1 className="dw-display">{t("plansFor", { date: dateLabel })}</h1>
          <GuideButton screen="plans" onOpen={onGuide} />
        </div>
        <PageBanners day={day} backendConnected={backendConnected} />
        <section className="dw-card dw-empty-card" aria-labelledby="dw-no-plans-title">
          <span className="dw-empty-tile"><Icon name="agent" size={24} /></span>
          <h2 id="dw-no-plans-title" className="dw-title">{past ? t("noPlansPast") : t("noPlansTitle")}</h2>
          {!past && <p className="dw-body-lg">{t("noPlansHelp")}</p>}
          {!past && (
            <div className="dw-actions">
              <button type="button" className="dw-button dw-button-primary" disabled={needsTask || !backendConnected || proposing}
                aria-busy={proposing} aria-describedby={needsTask || !backendConnected ? "dw-propose-reason" : undefined} onClick={onPropose}>
                <Icon name="agent" size={18} />{t(proposing ? "proposingAction" : "proposePlansAction")}
              </button>
              {(needsTask || !backendConnected) && <span id="dw-propose-reason" className="dw-caption">{needsTask ? t("proposeNeedsTask") : t("previewCannotSave")}</span>}
            </div>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="dw-page dw-plans" tabIndex={-1} ref={pageRef}>
      <header className="dw-page-head">
        <div>
          {back}
          <div className="dw-title-guide">
            <h1 className="dw-display">{t("plansFor", { date: dateLabel })}</h1>
            <GuideButton screen="plans" onOpen={onGuide} />
          </div>
          <div className="dw-chips">
            {setVariant
              ? <span className="dw-chip dw-chip-ink"><Icon name="check" size={14} />{t("planSetChip")} · {nameOf(setVariant)}{setAt && ` · ${setAt}`}</span>
              : <>
                <span className="dw-chip dw-chip-dashed"><Icon name="agent" size={14} />{t("draftsProposed", { count: variants.length })}</span>
                <span className="dw-chip"><Icon name="info" size={14} />{t("noPlanSetYet")}</span>
              </>}
            {past && <span className="dw-chip dw-chip-history"><Icon name="lock" size={14} />{t("readOnlyPastDay")}</span>}
          </div>
          {!setVariant && !past && <p className="dw-caption dw-page-note">{t("nothingScheduledUntil")}</p>}
        </div>
        {!past && (
          <div className="dw-page-actions">
            <button type="button" className="dw-button" disabled={!backendConnected || proposing} aria-busy={proposing}
              title={t("proposeAgainHelp")} onClick={onProposeAgain}>
              <Icon name="repeat" size={18} />{t(proposing ? "proposingAction" : "proposeAgainAction")}</button>
            <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAskDifferent}><Icon name="talk" size={18} />{t("askDifferentPlans")}</button>
          </div>
        )}
      </header>

      <PageBanners day={day} backendConnected={backendConnected} />
      {past && <p className="dw-banner dw-banner-history" role="note"><Icon name="lock" size={18} />{t("pastPlansHelp")}</p>}
      {error && <p className="dw-alert" role="alert">{error}</p>}

      <div className="dw-page-body">
      {narrow && variants.length > 1 && (
        <Segmented className="dw-plan-switch" label={t("plansSwitch")} value={shown.id} onChange={setShownId}
          options={variants.map((variant) => [variant.id, nameOf(variant)])} />
      )}
      <div className={`dw-plan-columns${narrow ? " dw-plan-single" : ""}`}>
        {(narrow ? [shown] : variants).map((variant) => (
          <PlanColumn key={variant.id} variant={variant} detail={details[variant.id]} dayItems={day.dayItems}
            isSet={variant.id === setId} isChosen={!narrow && variant.id === chosenId} past={past}
            showFoot={!past && !narrow} setAt={setAt} onChoose={() => choose(variant)} />
        ))}
      </div>
      {narrow && variants.length > 1 && (
        <div className="dw-plan-pager">
          <button type="button" className="dw-button dw-icon-only" aria-label={t("previousPlan")} disabled={shown === variants[0]} onClick={() => step(-1)}><Icon name="left" size={18} /></button>
          <span className="dw-caption">{t("planOfCount", { index: variants.indexOf(shown) + 1, count: variants.length })}</span>
          <button type="button" className="dw-button dw-icon-only" aria-label={t("nextPlan")} disabled={shown === variants[variants.length - 1]} onClick={() => step(1)}><Icon name="right" size={18} /></button>
        </div>
      )}

      <section className="dw-card dw-agent-notes" aria-label={t("agentNotesHeading")}>
        <SideTabs label={t("agentNotesHeading")} tabs={[
          ...(day.planRoute?.length > 0 ? [["agents", t("agentNotesHeading"), <AgentFindings key="agents" route={day.planRoute} />]] : []),
          ["types", t("planTypesTab"), <PlanTypes key="types" />],
        ]} />
      </section>
      </div>

      <div className="dw-setbar-slot" aria-live="polite">
        {candidate && (
          <SetBar name={nameOf(candidate)} count={details[candidate.id]?.entries.length || 0} narrow={narrow}
            question={day.date === today ? t("setTodayQuestion", { name: nameOf(candidate) }) : t("setDayQuestion", { name: nameOf(candidate), date: dateLabel })}
            backendConnected={backendConnected} onKeep={() => setChosenId(null)} onSet={() => onSet(candidate.id, false)} />
        )}
        {narrow && !past && setVariant && shown.id !== setId && (
          <div className="dw-setbar dw-setbar-narrow">
            <div className="dw-setbar-text"><p>{t("planIsSet", { name: nameOf(setVariant) })}</p></div>
            <div className="dw-setbar-actions">
              <button type="button" className="dw-button" onClick={() => choose(shown)}>{t("reviewReplaceWith", { name: nameOf(shown) })}</button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
