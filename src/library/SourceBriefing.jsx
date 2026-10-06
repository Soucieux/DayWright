import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { WORD_LIMIT, countWords } from "../wording";
import { useLibrary } from "./libraryContext";
import { briefingView, openActions, sourceView } from "./libraryData";

/** First-level headings, and second-level ones under each, a briefing lists before "and N more". */
const SHOWN_HEADINGS = 8;
const SHOWN_TOPICS = 6;
/** The longest briefing the Library keeps, in characters, as the local service takes it. */
const BRIEFING_CHARACTERS = 600;
/** Space kept between the pop-over and the name that opened it, and the window's edges. */
const GAP = 8;
const EDGE = 16;

/** Interface text for each kind of item. */
const KIND_KEYS = { markdown: "kindMarkdown", pdf: "kindPdf", word: "kindWord", file: "kindFile", note: "kindNote", website: "kindWebsite" };
/** The icon for each group of items. */
const GROUP_ICONS = { folders: "folder", websites: "globe", files: "file", notes: "note" };

/**
 * Who a briefing or an outline is by, as a short line: Ava, the user, or a website's own description.
 * @param {string} by - `ava`, `you`, `source` or "".
 * @param {string} origin - Where the item came from.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string|null} The line, or null for the item's own words.
 */
function byLine(by, origin, t) {
  if (by === "ava") return t("briefingSuggestedByAva");
  if (by === "you") return t("briefingWrittenByYou");
  return by === "source" && origin === "website" ? t("briefingFromSite") : null;
}

/**
 * Where the pop-over sits: under the name that opened it, or above it when there's no room below,
 * kept inside the window. On a phone's width the stylesheet sets it along the bottom instead.
 * @param {DOMRect} anchor - The name's box.
 * @param {DOMRect} card - The pop-over's box.
 * @returns {{top: number, left: number}} Its place in the window.
 */
function placeBeside(anchor, card) {
  const below = anchor.bottom + GAP;
  const lowest = window.innerHeight - EDGE - card.height;
  const top = below <= lowest ? below : Math.max(EDGE, Math.min(anchor.top - GAP - card.height, lowest));
  const left = Math.min(Math.max(EDGE, anchor.left), Math.max(EDGE, window.innerWidth - EDGE - card.width));
  return { top, left };
}

/**
 * Ava's briefing for an item without one of its own, or the user's: asked for, shown for editing, and
 * kept only on Confirm. Without the local model, or for a website that gives too little, the reason
 * shows and the user types it.
 * @param {object} props
 * @param {object} props.source - The item.
 * @param {boolean} props.wantsHeadings - Whether the item has no headings of its own, so some may be suggested.
 * @param {boolean} props.askAva - Ask Ava for a suggestion first; otherwise the user writes it.
 * @param {() => Promise<void>} props.onSaved - Reload the Library once it is kept.
 * @param {() => void} props.onCancel - Leave it as it was.
 */
function BriefingDraft({ source, wantsHeadings, askAva, onSaved, onCancel }) {
  const { t } = useI18n();
  const [asking, setAsking] = useState(askAva);
  const [suggestion, setSuggestion] = useState(null);
  const [briefing, setBriefing] = useState(source.briefing || "");
  const [headings, setHeadings] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const countId = useId();

  useEffect(() => {
    if (!askAva) return undefined;
    let live = true;
    api(`/api/sources/${encodeURIComponent(source.id)}/suggest-briefing`, { method: "POST" })
      .then((answer) => {
        if (!live) return;
        setSuggestion(answer);
        if (answer.briefing) setBriefing(answer.briefing);
        setHeadings((answer.outline || []).join("\n"));
      })
      .catch((caught) => { if (live) setError(caught.message); })
      .finally(() => { if (live) setAsking(false); });
    return () => { live = false; };
  }, [askAva, source.id]);

  const lines = headings.split("\n").map((line) => line.trim()).filter(Boolean);
  // A suggestion kept as Ava wrote it is hers; one the user changed, or wrote, is theirs.
  const unchanged = suggestion && (suggestion.briefing ?? source.briefing ?? "") === briefing
    && (suggestion.outline || []).join("\n") === lines.join("\n");
  const changedBriefing = briefing.trim() && briefing.trim() !== (source.briefing || "");
  // A briefing holds at most the word limit; Confirm waits until it does.
  const over = countWords(briefing) > WORD_LIMIT;

  async function confirm(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api(`/api/sources/${encodeURIComponent(source.id)}/briefing`, { method: "PUT", body: JSON.stringify({
        briefing: changedBriefing ? briefing.trim() : null, outline: lines.length ? lines : null, by: unchanged ? "ava" : "you" }) });
      await onSaved();
    } catch (caught) {
      setError(caught.message);
      setSaving(false);
    }
  }

  if (asking) return <p className="dw-caption dw-briefing-asking" role="status"><Icon name="agent" size={16} />{t("briefingAsking")}</p>;
  return (
    <form className="dw-form dw-briefing-draft" onSubmit={confirm}>
      {suggestion && <p className="dw-evidence dw-pencilled"><Icon name="agent" size={16} /><span>{t("briefingEditNote")}</span></p>}
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <label className="dw-field">{t("briefingLabel")}
        <textarea rows={3} maxLength={BRIEFING_CHARACTERS} value={briefing} aria-describedby={countId}
          onChange={(event) => setBriefing(event.target.value)} />
        <span id={countId} className={`dw-caption${over ? " dw-word-over" : ""}`}>
          {t("wordCountLine", { count: countWords(briefing), limit: WORD_LIMIT })}</span></label>
      {wantsHeadings && (
        <label className="dw-field">{t("briefingHeadingsLabel")}
          <textarea rows={4} value={headings} onChange={(event) => setHeadings(event.target.value)} /></label>
      )}
      <div className="dw-actions">
        <button type="submit" className="dw-button dw-button-primary" disabled={saving || over || (!changedBriefing && !lines.length)}>
          <Icon name="check" size={18} />{saving ? t("savingLabel") : t("confirmBriefingAction")}</button>
        <button type="button" className="dw-button dw-button-quiet" onClick={onCancel}>{t("cancel")}</button>
      </div>
    </form>
  );
}

/**
 * A Library item's briefing, beside the name that opened it: what it is about, who said so, and its
 * first- and second-level headings; never its text. A connected folder's file opens in its app or on
 * its folder's website, and a website in the browser. Where the briefing or headings are missing,
 * Ava can suggest them, or the user writes them. Escape, Close or a click elsewhere closes it.
 * @param {object} props
 * @param {object} props.source - The item, as the local service lists it.
 * @param {string} props.name - Its name as shown.
 * @param {{current: HTMLElement|null}} props.anchorRef - The name that opened it.
 * @param {() => void} props.onClose - Close it, returning to the name.
 */
export function SourceBriefing({ source, name, anchorRef, onClose }) {
  const { t, demoText } = useI18n();
  const { folders, backendConnected, refresh } = useLibrary();
  const titleId = useId();
  const cardRef = useRef(null);
  const [place, setPlace] = useState({ top: -9999, left: -9999 });
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState("");
  const view = sourceView(source);
  const briefing = briefingView(source);
  const folder = folders.find((entry) => entry.id === source.folderId);
  const opens = openActions(source, folder);
  const by = byLine(briefing.by, source.origin, t);

  // It is placed again whenever it changes size, as a briefing to write opens in it, and as the window
  // or the page under it moves, so it never runs off the screen where it couldn't be scrolled to.
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!card) return undefined;
    const place = () => {
      if (anchorRef.current) setPlace(placeBeside(anchorRef.current.getBoundingClientRect(), card.getBoundingClientRect()));
    };
    place();
    const watcher = new ResizeObserver(place);
    watcher.observe(card);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      watcher.disconnect();
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [anchorRef]);

  // Focus moves in once, as it opens; a click outside it, but not on its name, closes it.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => cardRef.current?.focus(), []);
  useEffect(() => {
    function onPointer(event) {
      if (!cardRef.current?.contains(event.target) && !anchorRef.current?.contains(event.target)) closeRef.current();
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [anchorRef]);

  function onKeyDown(event) {
    // Escape closes only the pop-over, not a sheet it was opened from.
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); }
  }

  /**
   * Open the item where it lives.
   * @param {"app"|"website"} where - In its app, or on its folder's website; a website always opens in the browser.
   */
  async function open(where) {
    setError("");
    try {
      await api(`/api/sources/${encodeURIComponent(source.id)}/open`, { method: "POST", body: JSON.stringify({ where }) });
    } catch (caught) {
      setError(t("openFailed", { reason: caught.message }));
    }
  }

  async function saved() {
    setDraft(null);
    await refresh();
  }

  const headings = briefing.headings.slice(0, SHOWN_HEADINGS);
  return createPortal(
    <div ref={cardRef} className="dw-briefing" role="dialog" aria-labelledby={titleId} tabIndex={-1}
      style={{ top: place.top, left: place.left }} onKeyDown={onKeyDown}>
      <div className="dw-briefing-head">
        <Icon name={GROUP_ICONS[view.group]} size={20} />
        <span className="dw-briefing-title">
          <h3 id={titleId} className="dw-heading">{name}</h3>
          <span className="dw-caption">{t(KIND_KEYS[view.kind])}{folder ? ` · ${folder.title}` : ""}</span>
        </span>
        <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("closeAction")} title={t("closeAction")}
          onClick={onClose}><Icon name="x" size={18} /></button>
      </div>
      <section aria-labelledby={`${titleId}-about`}>
        <h4 id={`${titleId}-about`} className="dw-eyebrow">{t("briefingAbout")}</h4>
        <p className={briefing.text ? undefined : "dw-muted"}>{briefing.text ? demoText(briefing.text) : t("noBriefingYet")}</p>
        {briefing.text && by && <p className="dw-caption dw-briefing-by">{briefing.by === "ava" && <Icon name="agent" size={14} />}{by}</p>}
      </section>
      <section aria-labelledby={`${titleId}-headings`}>
        <h4 id={`${titleId}-headings`} className="dw-eyebrow">{t("headingsTitle")}</h4>
        {headings.length ? (
          <ul className="dw-briefing-headings">
            {headings.map((heading, index) => (
              <li key={`${index}-${heading.title}`}>{demoText(heading.title)}
                {heading.topics.length > 0 && (
                  <ul>
                    {heading.topics.slice(0, SHOWN_TOPICS).map((topic, at) => <li key={`${at}-${topic}`}>{demoText(topic)}</li>)}
                    {heading.topics.length > SHOWN_TOPICS && <li className="dw-caption">{t("moreHeadings", { count: heading.topics.length - SHOWN_TOPICS })}</li>}
                  </ul>
                )}
              </li>
            ))}
            {briefing.headings.length > SHOWN_HEADINGS && <li className="dw-caption">{t("moreHeadings", { count: briefing.headings.length - SHOWN_HEADINGS })}</li>}
          </ul>
        ) : <p className="dw-muted">{t("noHeadingsYet")}</p>}
        {headings.length > 0 && briefing.outlineBy === "ava" && (
          <p className="dw-caption dw-briefing-by"><Icon name="agent" size={14} />{t("briefingSuggestedByAva")}</p>
        )}
        {source.progress?.total > 0 && (
          <p className="dw-caption dw-briefing-by"><Icon name="check" size={14} />{t("checklistProgress", source.progress)}</p>
        )}
      </section>
      {draft ? (
        <BriefingDraft key={draft} source={source} askAva={draft === "ava"} onSaved={saved} onCancel={() => setDraft(null)}
          wantsHeadings={!briefing.headings.length && source.origin !== "website"} />
      ) : briefing.wants && backendConnected && (
        <div className="dw-briefing-actions">
          <button type="button" className="dw-button" onClick={() => setDraft("ava")}><Icon name="agent" size={18} />{t("askAvaBriefing")}</button>
          <button type="button" className="dw-button dw-button-quiet" onClick={() => setDraft("you")}><Icon name="pencil" size={18} />{t("writeBriefingAction")}</button>
        </div>
      )}
      {(opens.app || opens.website || opens.browser) && (
        <div className="dw-briefing-actions">
          {opens.app && <button type="button" className="dw-button" disabled={!backendConnected} onClick={() => open("app")}>
            <Icon name="external" size={18} />{t("openAction")}</button>}
          {opens.website && <button type="button" className="dw-button" disabled={!backendConnected} onClick={() => open("website")}>
            <Icon name="globe" size={18} />{t("openOnWebsiteAction")}</button>}
          {opens.browser && <button type="button" className="dw-button" disabled={!backendConnected} onClick={() => open("app")}>
            <Icon name="globe" size={18} />{t("openAction")}</button>}
          {opens.browser && <span className="dw-caption">{t("opensInBrowser")}</span>}
        </div>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </div>,
    document.body,
  );
}

/**
 * A Library item's name as a button that opens its briefing beside it, wherever the item is listed.
 * @param {object} props
 * @param {object} props.source - The item, as the local service lists it.
 * @param {string} [props.className] - Extra classes for the button.
 * @param {React.ReactNode} [props.children] - What the button shows; its name by default.
 */
export function BriefingButton({ source, className = "", children }) {
  const { t, demoText } = useI18n();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);
  const name = demoText(sourceView(source).name);

  function close() {
    setOpen(false);
    buttonRef.current?.focus();
  }

  return (
    <>
      <button ref={buttonRef} type="button" className={`dw-briefing-name ${className}`.trim()} aria-haspopup="dialog" aria-expanded={open}
        title={t("showBriefingLabel", { name })} onClick={() => setOpen((shown) => !shown)}>{children || name}</button>
      {open && <SourceBriefing source={source} name={name} anchorRef={buttonRef} onClose={close} />}
    </>
  );
}
