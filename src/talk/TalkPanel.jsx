import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { shortDate } from "../time";
import { ProposalCard } from "./ProposalCard";
import { TalkMessage } from "./TalkMessage";
import { usePushToTalk } from "./usePushToTalk";

/** Talk's modes, in switch order. */
const MODES = ["ask", "adjust", "report"];

/** The composer's hint for each mode. */
const PLACEHOLDER_KEYS = { ask: "askPlaceholder", adjust: "adjustPlaceholder", report: "reportPlaceholder" };

/** Each place's name, for the context chip. */
const PLACE_KEYS = { today: "navToday", calendar: "navCalendar", records: "navRecords", library: "navLibrary" };

/** The Hold to talk button's label while listening goes through its states. */
const HOLD_KEYS = { idle: "holdToTalk", starting: "micStarting", listening: "releaseToSend", transcribing: "voiceTranscribing" };

/** The footer line for each state of the local chat model. */
const MODEL_KEYS = { ready: "modelFooterReady", available: "modelFooterStandby" };

/**
 * Talk, reachable from every place: docked beside the page on desktop and a sheet on phone. It
 * carries the place and day on show, answers in Ask, Adjust or Report mode, shows how each reply
 * was made, and keeps any proposal pencilled until the user confirms it. It stays mounted while
 * closed so a draft and an open proposal survive.
 * @param {object} props
 * @param {boolean} props.open - Whether Talk is showing.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {string} props.place - The place on show: `today`, `calendar`, `records` or `library`.
 * @param {string} props.mode - `ask`, `adjust` or `report`.
 * @param {(mode: string) => void} props.onMode - Change mode.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {() => void} props.onClose - Close Talk.
 * @param {(model: object|null, variantId?: string, changedDate?: string) => Promise<void>} props.onUpdated -
 *   Refresh after a reply (with the model's status) or a confirmed change (with what changed).
 */
export function TalkPanel({ open, day, today, place, mode, onMode, backendConnected, onClose, onUpdated }) {
  const { t, language } = useI18n();
  const [messages, setMessages] = useState(day.messages || []);
  const [proposals, setProposals] = useState({});
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [voiceNote, setVoiceNote] = useState("");
  const panelRef = useRef(null);
  const logRef = useRef(null);
  const draftRef = useRef(null);
  const openerRef = useRef(null);
  const voice = usePushToTalk((text) => send(text, true), setVoiceNote);
  const voiceReady = backendConnected && day.voice?.state === "available";

  useEffect(() => setMessages(day.messages || []), [day.messages]);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages, sending, open]);

  // Opening moves focus to the composer; closing stops any recording and returns focus to what
  // opened Talk, unless the user has already moved on to something else.
  useEffect(() => {
    if (open) {
      openerRef.current = document.activeElement;
      draftRef.current?.focus();
      return;
    }
    voice.finish(false);
    const opener = openerRef.current;
    openerRef.current = null;
    const focusWasHere = panelRef.current?.contains(document.activeElement) || document.activeElement === document.body;
    if (opener && focusWasHere) (opener.isConnected ? opener : document.querySelector("main"))?.focus();
  }, [open]);

  /**
   * Send words to the agents and show their reply, with any proposal it carries.
   * @param {string} text - What the user typed or said.
   * @param {boolean} [spoken] - Whether it was transcribed from speech.
   */
  async function send(text, spoken = false) {
    const words = text.trim();
    if (!words || sending || !backendConnected) return;
    if (!spoken) setDraft("");
    setSending(true);
    setError("");
    setMessages((current) => [...current, { id: `local-${Date.now()}`, role: "user", mode, content: words, voice: spoken }]);
    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ date: day.date, message: words, mode, selectedVariantId: day.selectedVariantId, language }),
      });
      setMessages((current) => [...current, result.assistantMessage]);
      if (result.proposedAction) setProposals((current) => ({ ...current, [result.assistantMessage.id]: result.proposedAction }));
      onUpdated(result.model);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSending(false);
    }
  }

  function onPanelKey(event) {
    if (event.key === "Escape" && voice.state === "idle") {
      event.stopPropagation();
      onClose();
    }
  }

  function onHoldKeyDown(event) {
    if ((event.key === " " || event.key === "Enter") && !event.repeat) {
      event.preventDefault();
      setVoiceNote("");
      voice.start();
    } else if (event.key === "Escape" && voice.state !== "idle") {
      event.preventDefault();
      event.stopPropagation();
      voice.finish(false);
    }
  }

  function onHoldKeyUp(event) {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      voice.finish(true);
    }
  }

  const voiceLine = voiceNote || (voice.state === "listening" ? t("listeningStatus")
    : !backendConnected ? "" : voiceReady ? t("voiceHint") : t("voiceSetup"));
  const modelLine = !backendConnected ? t("talkNeedsService") : t(MODEL_KEYS[day.model?.state] || "modelFooterOff");

  return (
    <>
      <button type="button" className="dw-talk-scrim" hidden={!open} tabIndex={-1} aria-hidden="true" onClick={onClose} />
      <aside className="dw-talk-panel" hidden={!open} ref={panelRef} aria-labelledby="dw-talk-title" onKeyDown={onPanelKey}>
        <span className="dw-talk-grip" aria-hidden="true" />
        <header className="dw-talk-head">
          <div className="dw-talk-title">
            <h2 id="dw-talk-title">{t("navTalk")}</h2>
            <span className="dw-chip dw-chip-small">{t("contextChip", { place: t(PLACE_KEYS[place]), date: shortDate(day.date, language) })}</span>
            <button type="button" className="dw-icon-button" aria-label={t("closeTalk")} onClick={onClose}><Icon name="x" size={20} /></button>
          </div>
          <Segmented className="dw-talk-modes" label={t("talkModes")} value={mode} onChange={onMode} options={MODES.map((id) => [id, t(id)])} />
          <p className="dw-caption">{t(`${mode}Help`)}</p>
        </header>

        <div className="dw-talk-log" ref={logRef} aria-live="polite">
          {messages.length === 0 && !sending && (
            <p className="dw-talk-empty"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span><span>{t("orchestratorHelp")}</span></p>
          )}
          {messages.map((message) => (
            <TalkMessage key={message.id} message={message} demoMode={Boolean(day.demoMode)}>
              {proposals[message.id] && (
                <ProposalCard proposal={proposals[message.id]} day={day} today={today} backendConnected={backendConnected}
                  onConfirmed={(payload) => onUpdated(null, payload.variantId, payload.date)} />
              )}
            </TalkMessage>
          ))}
          {sending && <p className="dw-talk-empty" role="status"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span><span>{t("consulting")}</span></p>}
          {error && <p className="dw-alert" role="alert">{error}</p>}
        </div>

        <form className="dw-talk-compose" onSubmit={(event) => { event.preventDefault(); send(draft); }}>
          <div className="dw-talk-compose-row">
            <label className="dw-visually-hidden" htmlFor="dw-talk-draft">{t("messageLabel")}</label>
            <textarea id="dw-talk-draft" ref={draftRef} rows={1} value={draft} disabled={!backendConnected} placeholder={t(PLACEHOLDER_KEYS[mode])}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(draft); } }} />
            <button type="button" className="dw-button dw-hold" aria-pressed={voice.state === "listening"} aria-describedby="dw-talk-voice"
              disabled={!voiceReady || sending || voice.state === "transcribing"}
              onPointerDown={(event) => { event.preventDefault(); setVoiceNote(""); voice.start(); }}
              onPointerUp={() => voice.finish(true)}
              onPointerLeave={() => { if (voice.state !== "idle") voice.finish(false); }}
              onPointerCancel={() => voice.finish(false)}
              onKeyDown={onHoldKeyDown} onKeyUp={onHoldKeyUp}>
              <Icon name="mic" size={18} />{t(HOLD_KEYS[voice.state])}
            </button>
            <button type="submit" className="dw-button dw-button-primary dw-send" aria-label={t("send")} disabled={!backendConnected || !draft.trim() || sending}><Icon name="send" size={18} /></button>
          </div>
          {voiceLine && <p id="dw-talk-voice" className="dw-caption" role="status">{voiceLine}</p>}
          <p className="dw-caption dw-talk-foot"><Icon name="chip" size={14} />{modelLine}</p>
        </form>
      </aside>
    </>
  );
}
