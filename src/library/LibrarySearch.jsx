import { useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { findInLibrary, matchView } from "./libraryData";
import { BriefingButton } from "./SourceBriefing";
import { LibraryItemList } from "./SourceList";

/** The most passages one search shows. */
const MOST_PASSAGES = 8;

/**
 * Search the Library on this Mac: first the items whose name, briefing or headings hold the words,
 * websites among them, then passages found by meaning with the local embedding model, across the whole
 * Library. Each name opens its briefing; each passage shows its item, that one's goal, and which part it
 * is; Ask Ava opens Ava with a question about the search typed in.
 * @param {object} props
 * @param {object[]} props.items - Every item in the Library.
 * @param {boolean} props.backendConnected - Whether a search can run.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a question typed in and not sent.
 */
export function LibrarySearch({ items, backendConnected, onAskAva }) {
  const { t, demoText } = useI18n();
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState("");
  const [result, setResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const queryRef = useRef(null);

  /**
   * Search the Library for some words.
   * @param {string} words - What to look for.
   */
  async function search(words) {
    setSearching(true);
    setError("");
    try {
      setResult(await api("/api/knowledge/search", { method: "POST", body: JSON.stringify({ query: words, limit: MOST_PASSAGES }) }));
      setAsked(words);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSearching(false);
    }
  }

  function clear() {
    setResult(null);
    setAsked("");
    queryRef.current?.focus();
  }

  const matches = result?.matches || [];
  const named = result ? findInLibrary(items, asked) : [];
  const itemOf = (match) => items.find((item) => item.id === match.sourceId);
  return (
    <section className="dw-library-search" aria-labelledby="dw-search-label">
      <form role="search" className="dw-search-form" onSubmit={(event) => { event.preventDefault(); if (query.trim()) search(query.trim()); }}>
        <label id="dw-search-label" htmlFor="dw-library-query" className="dw-visually-hidden">{t("searchLibraryLabel")}</label>
        <span className="dw-search"><Icon name="search" size={18} />
          <input id="dw-library-query" ref={queryRef} type="search" maxLength={200} value={query} placeholder={t("searchLibraryLabel")}
            disabled={!backendConnected} onChange={(event) => setQuery(event.target.value)} /></span>
        <button type="submit" className="dw-button" disabled={!backendConnected || !query.trim() || searching}>
          {searching ? t("searchingLabel") : t("searchAction")}</button>
      </form>
      <div className="dw-search-results" aria-live="polite">
        {error && <p className="dw-alert" role="alert">{error}</p>}
        {result && (
          <section className="dw-card dw-matches-card" aria-labelledby="dw-matches-title">
            <div className="dw-card-head">
              <h2 id="dw-matches-title" className="dw-heading">{t("searchResultsHeading", { query: asked, count: matches.length })}</h2>
              <button type="button" className="dw-link" onClick={clear}>{t("clearSearchAction")}</button>
            </div>
            {named.length > 0 && (
              <div className="dw-named-matches">
                <h3 className="dw-eyebrow">{t("findInLibraryHeading", { count: named.length })}</h3>
                <LibraryItemList items={named} />
              </div>
            )}
            {result.status === "unavailable" ? <p className="dw-banner dw-banner-caution"><Icon name="alert" size={18} />{t("localSearchUnavailable")}</p>
              : result.status === "empty" ? <p className="dw-muted">{t("libraryEmptySearch")}</p>
                : !matches.length ? <p className="dw-muted">{t("noLocalMatch")}</p> : (
                  <>
                    <ul className="dw-matches">
                      {matches.map((match) => {
                        const view = matchView(match);
                        const item = itemOf(match);
                        return (
                          <li key={match.chunkId} className="dw-match">
                            <span className="dw-match-head"><Icon name={match.sourceType === "document" ? "file" : "note"} size={18} />
                              {item ? <BriefingButton source={item} /> : <span>{demoText(view.name)}</span>}<span className="dw-spacer" /><span className="dw-caption">{t("passagePart", { part: view.part })}</span></span>
                            <p>“{demoText(view.passage)}”</p>
                          </li>
                        );
                      })}
                    </ul>
                    <button type="button" className="dw-button dw-search-ask" onClick={() => onAskAva(t("askAvaAboutSearch", { query: asked }))}>
                      <Icon name="talk" size={18} />{t("askTalkAboutThis")}</button>
                  </>
                )}
          </section>
        )}
      </div>
    </section>
  );
}
