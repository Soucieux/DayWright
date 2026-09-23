import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { fullDate, localDateOf } from "../time";
import { PUBLIC_SOURCE_HOST } from "./libraryData";

/** The local service's names for ways to organize a public introduction, and their interface text. */
const ORGANIZATION_KEYS = {
  "By level": "organizeByLevel", "By method": "organizeByMethod", "By progression": "organizeByProgression",
  Basic: "labelBasic", Advanced: "labelAdvanced", Practical: "labelPractical",
  Theory: "labelTheory", "Case Study": "labelCaseStudy", Exercise: "labelExercise",
  Introduction: "labelIntroduction", Core: "labelCore", Extension: "labelExtension",
};

/**
 * What a lookup's single online request would carry, asked before anything is sent.
 * @param {object} props
 * @param {string} props.topic - The words that would be sent.
 * @param {boolean} props.fetching - Whether the request is under way.
 * @param {() => void} props.onFetch - Send the request.
 * @param {() => void} props.onDecline - Send nothing.
 */
function ConsentCard({ topic, fetching, onFetch, onDecline }) {
  const { t } = useI18n();
  return (
    <section className="dw-consent" aria-labelledby="dw-consent-title">
      <div className="dw-consent-head">
        <span className="dw-consent-tile"><Icon name="globe" size={22} /></span>
        <h3 id="dw-consent-title" className="dw-heading">{t("fetchIntroQuestion")}</h3>
      </div>
      <dl className="dw-consent-terms">
        <dt>{t("consentSends")}</dt><dd>{t("consentSendsWords", { topic })}</dd>
        <dt>{t("consentTo")}</dt><dd>{PUBLIC_SOURCE_HOST}</dd>
        <dt>{t("consentKeeps")}</dt><dd>{t("consentKeepsWhat")}</dd>
        <dt>{t("consentNeverSends")}</dt><dd>{t("consentNeverWhat")}</dd>
      </dl>
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-primary" disabled={fetching} onClick={onFetch}><Icon name="globe" size={18} />{fetching ? t("fetchingLabel") : t("fetchIntroAction")}</button>
        <button type="button" className="dw-button" disabled={fetching} onClick={onDecline}>{t("notNowAction")}</button>
      </div>
      <p className="dw-caption">{t("asksEveryTime")}</p>
    </section>
  );
}

/**
 * A fetched public introduction waiting for the user: where it came from, how to organize it, and
 * whether to keep it. Nothing is saved until the user chooses.
 * @param {object} props
 * @param {object} props.options - The staged introduction and its ways to organize it.
 * @param {string} props.planId - The chosen way.
 * @param {(planId: string) => void} props.onPlan - Choose a way.
 * @param {boolean} props.saving - Whether it is being saved.
 * @param {() => void} props.onKeep - Save it as a note.
 * @param {() => void} props.onLater - Leave it waiting.
 */
function ImportChoice({ options, planId, onPlan, saving, onKeep, onLater }) {
  const { t, language } = useI18n();
  const named = (text) => (ORGANIZATION_KEYS[text] ? t(ORGANIZATION_KEYS[text]) : text);
  const edited = Number.isNaN(Date.parse(options.filter?.timeliness)) ? "" : fullDate(localDateOf(options.filter.timeliness), language);
  return (
    <section className="dw-import-choice" aria-labelledby="dw-import-title">
      <h3 id="dw-import-title" className="dw-heading">{t("keepIntroQuestion")}</h3>
      <p className="dw-caption"><a href={options.sourceUrl} target="_blank" rel="noopener noreferrer">{options.sourceTitle}</a> · {options.sourceLicense}</p>
      <p className="dw-muted">{t("encyclopediaNote")}</p>
      {edited && <p className="dw-caption">{t("lastEdited", { date: edited })}</p>}
      <fieldset className="dw-choice-list">
        <legend className="dw-field-label">{t("organizeAs")}</legend>
        {options.plans.map((plan) => (
          <label key={plan.id} className="dw-choice">
            <input type="radio" name={`dw-organize-${options.acquisitionId}`} checked={planId === plan.id} onChange={() => onPlan(plan.id)} />
            <span><strong>{named(plan.name)}</strong><span className="dw-caption">{plan.labels.map(named).join(" / ")}</span></span>
          </label>
        ))}
      </fieldset>
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-primary" disabled={!planId || saving} onClick={onKeep}><Icon name="note" size={18} />{saving ? t("savingLabel") : t("saveAsNoteAction")}</button>
        <button type="button" className="dw-button dw-button-quiet" disabled={saving} onClick={onLater}>{t("notNowAction")}</button>
      </div>
      <p className="dw-caption">{t("choiceWaits")}</p>
    </section>
  );
}

/**
 * Local passages that matched a lookup, quoted with where they come from.
 * @param {object} props
 * @param {object[]} props.matches - Matching passages, best first.
 * @param {() => void} props.onAskTalk - Open Talk to ask about them.
 */
function LocalMatches({ matches, onAskTalk }) {
  const { t, demoText } = useI18n();
  return (
    <section className="dw-matches-section" aria-labelledby="dw-matches-title">
      <div className="dw-card-head">
        <h3 id="dw-matches-title" className="dw-section-label">{t("fromYourLibrary", { count: matches.length })}</h3>
        <span className="dw-chip dw-chip-small dw-chip-saved"><Icon name="laptop" size={14} />{t("localOnly")}</span>
      </div>
      <ul className="dw-matches">
        {matches.map((match) => (
          <li key={match.chunkId || `${match.sourceId}-${match.chunkIndex}`} className="dw-match">
            <span className="dw-match-head"><Icon name={match.sourceType === "document" ? "file" : "note"} size={18} />
              <span>{demoText(match.sourceTitle)}</span><span className="dw-spacer" /><span className="dw-caption">§{match.chunkIndex + 1}</span></span>
            <p>“{demoText(match.content)}”</p>
          </li>
        ))}
      </ul>
      <button type="button" className="dw-button dw-lookup-talk" onClick={onAskTalk}><Icon name="talk" size={18} />{t("askTalkAboutThis")}</button>
    </section>
  );
}

/**
 * Look up a topic: in the Library first, and online only when the user allows it for this one
 * lookup, after seeing exactly what would be sent and where. A fetched introduction is saved only
 * when the user keeps it.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether lookups can run.
 * @param {() => void} props.onAskTalk - Open Talk to ask about what was found.
 * @param {() => Promise<void>} props.onSaved - Refresh after an introduction is saved.
 * @param {() => void} props.onNetwork - Refresh the network log after a request may have gone out.
 */
export function TopicLookup({ backendConnected, onAskTalk, onSaved, onNetwork }) {
  const { t } = useI18n();
  const [topic, setTopic] = useState("");
  const [allowPublic, setAllowPublic] = useState(false);
  const [busy, setBusy] = useState("");
  const [asked, setAsked] = useState("");
  const [result, setResult] = useState(null);
  const [planId, setPlanId] = useState("");
  const [pending, setPending] = useState([]);
  const [error, setError] = useState("");
  const lookupRef = useRef(null);
  const topicRef = useRef(null);

  // A result replaces the card whose button was pressed; keep focus in the lookup rather than lose it.
  useEffect(() => {
    if (result && !lookupRef.current?.contains(document.activeElement)) topicRef.current?.focus();
  }, [result]);

  useEffect(() => {
    if (!backendConnected) return;
    api("/api/knowledge/import-plans").then((response) => setPending(response.pending)).catch(() => setPending([]));
  }, [backendConnected]);

  /**
   * Run a lookup. Online only when `explicitWeb` is true, which only the user's switch or consent sets.
   * @param {string} words - The topic.
   * @param {boolean} explicitWeb - Whether the user allowed one online request for it.
   */
  async function lookUp(words, explicitWeb) {
    setBusy(explicitWeb ? "fetching" : "searching");
    setError("");
    try {
      const outcome = await api("/api/knowledge/topic", { method: "POST", body: JSON.stringify({ topic: words, explicitWeb }) });
      setAsked(words);
      setResult(outcome);
      setPlanId(outcome.importOptions?.plans[0]?.id || "");
      if (outcome.importOptions) setPending((items) => [outcome.importOptions, ...items]);
    } catch (caught) {
      setError(explicitWeb ? t("publicLookupFailed") : caught.message);
    } finally {
      setBusy("");
      setAllowPublic(false);
      if (explicitWeb) onNetwork();
    }
  }

  async function keep() {
    const options = result.importOptions;
    setBusy("saving");
    setError("");
    try {
      await api(`/api/knowledge/import-plans/${planId}/confirm`, { method: "POST" });
      setPending((items) => items.filter((item) => item.acquisitionId !== options.acquisitionId));
      setResult((current) => ({ ...current, publicFetch: "imported" }));
      await onSaved();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy("");
    }
  }

  /**
   * Show a fetched introduction that is still waiting for a choice.
   * @param {object} item - The staged introduction.
   */
  function review(item) {
    setAsked(item.topic);
    setError("");
    setResult({ publicFetch: "awaiting_import_choice", importOptions: item, retrieval: null });
    setPlanId(item.selectedPlanId || item.plans[0]?.id || "");
  }

  const status = result?.publicFetch;
  const matches = result?.retrieval?.matches || [];
  const choosing = status === "awaiting_import_choice" ? result.importOptions : null;
  const waiting = pending.filter((item) => item.acquisitionId !== choosing?.acquisitionId);

  return (
    <section className="dw-card dw-lookup" aria-labelledby="dw-lookup-title" ref={lookupRef}>
      <h2 id="dw-lookup-title" className="dw-title">{t("lookUpTitle")}</h2>
      <form className="dw-lookup-form" onSubmit={(event) => { event.preventDefault(); if (topic.trim()) lookUp(topic.trim(), allowPublic); }}>
        <div className="dw-field">
          <label htmlFor="dw-topic" className="dw-field-label">{t("topicLabel")}</label>
          <span className="dw-lookup-row">
            <span className="dw-search"><Icon name="search" size={18} />
              <input id="dw-topic" ref={topicRef} required maxLength={200} value={topic} disabled={!backendConnected} onChange={(event) => setTopic(event.target.value)} /></span>
            <button type="submit" className="dw-button" disabled={!backendConnected || !topic.trim() || Boolean(busy)}>{busy === "searching" ? t("searchingLabel") : t("lookUpAction")}</button>
          </span>
        </div>
        <label className="dw-switch">
          <input type="checkbox" role="switch" checked={allowPublic} disabled={!backendConnected} onChange={(event) => setAllowPublic(event.target.checked)} />
          <span><strong>{t("allowPublicIntro")}</strong>
            <span className="dw-caption">{allowPublic ? t("allowPublicOn", { destination: PUBLIC_SOURCE_HOST }) : t("allowPublicOff")}</span></span>
        </label>
        {!backendConnected && <p className="dw-caption">{t("lookupNeedsService")}</p>}
      </form>

      <div className="dw-lookup-results" aria-live="polite">
        {error && <p className="dw-alert" role="alert">{error}</p>}
        {result?.retrieval?.status === "unavailable" && <p className="dw-banner dw-banner-caution"><Icon name="alert" size={18} />{t("localSearchUnavailable")}</p>}
        {matches.length > 0 && <LocalMatches matches={matches} onAskTalk={onAskTalk} />}
        {status === "awaiting_consent" && (
          <>
            <p className="dw-lookup-note"><Icon name="search" size={18} />{result.retrieval?.status === "empty" ? t("libraryEmptySearch") : t("noLocalMatch")}</p>
            <ConsentCard topic={asked} fetching={busy === "fetching"} onFetch={() => lookUp(asked, true)}
              onDecline={() => setResult((current) => ({ ...current, publicFetch: "declined" }))} />
          </>
        )}
        {status === "declined" && <p className="dw-lookup-note"><Icon name="offline" size={18} />{t("nothingSentNote")}</p>}
        {status === "needs_general_topic" && (
          <div className="dw-refusal" role="alert">
            <h3><Icon name="alert" size={18} /> {t("personalTopicTitle")}</h3>
            <p>{t("personalTopicBody")}</p>
          </div>
        )}
        {choosing && <ImportChoice options={choosing} planId={planId} onPlan={setPlanId} saving={busy === "saving"} onKeep={keep}
          onLater={() => setResult((current) => ({ ...current, publicFetch: "later" }))} />}
        {status === "imported" && <p className="dw-banner dw-banner-saved" role="status"><Icon name="check" size={18} />{t("introSaved")}</p>}
      </div>

      {waiting.length > 0 && (
        <section aria-labelledby="dw-waiting-title">
          <h3 id="dw-waiting-title" className="dw-section-label">{t("waitingForChoice")}</h3>
          <ul className="dw-pending-list">
            {waiting.map((item) => (
              <li key={item.acquisitionId}><button type="button" className="dw-chip dw-chip-link" onClick={() => review(item)}>{t("reviewTopicChoice", { topic: item.topic })}</button></li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
