import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { shortDate } from "../time";
import { Icon } from "../ui/Icon";
import { AVA_MARGIN, AVA_MIN_HEIGHT, AVA_SIZE, avaFrame } from "./avaFrame";
import { ProposalCard } from "./ProposalCard";
import { talkLog } from "./notices";
import { starterPrompts } from "./starters";
import { TalkMessage, TalkNotice } from "./TalkMessage";
import { useDictation } from "./useDictation";

/** Where a moved Ava is remembered between launches, in this browser's own storage. */
const POSITION_KEY = "daywright-ava-position";
/** Where the height the user gave Ava is remembered. */
const HEIGHT_KEY = "daywright-ava-height";
/** Below this window width Ava is a sheet from the bottom, as on a phone, and can't be moved. */
const PHONE_WIDTH = 640;
/** How much each arrow key press on the resize handle changes Ava's height, in CSS pixels. */
const RESIZE_STEP = 40;

/**
 * Read a remembered value, or null; storage can be missing or refuse.
 * @param {string} key - The storage key.
 * @param {(value: unknown) => boolean} isValid - Whether a stored value can be used.
 */
function remembered(key, isValid) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return isValid(value) ? value : null;
  } catch {
    return null;
  }
}

/** Remember a value, or forget it given null; failing to store only loses a convenience. */
function remember(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ava opens in its corner, at its usual height, next time instead.
  }
}

const isPosition = (value) => Number.isFinite(value?.left) && Number.isFinite(value?.top);

/** The window's size, followed as it changes. */
function useViewport() {
  const [viewport, setViewport] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    const measure = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);
  return viewport;
}

/**
 * The width of a sheet open at the window's right, such as a task's or the Library's add sheet, or 0. Every
 * sheet opens in the sheet slot, so only the slot is watched, and the window's size.
 */
function useSheetWidth() {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const slot = document.getElementById("dw-sheet-slot");
    const measure = () => setWidth(Math.round(slot?.querySelector(".dw-sheet")?.getBoundingClientRect().width || 0));
    const observer = new MutationObserver(measure);
    if (slot) observer.observe(slot, { childList: true });
    window.addEventListener("resize", measure);
    measure();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);
  return width;
}

/** What the one button beside the box does, by what is in the box and whether Ava is listening. */
const ACTIONS = {
  speak: { icon: "mic", label: "avaSpeak" },
  stop: { icon: "stop", label: "avaStopListening" },
  send: { icon: "send", label: "send" },
};

/**
 * Ava, DayWright's assistant, reachable from every place: a window floating over the page on
 * desktop, which never moves the page, and a sheet on a phone. It works out from each message
 * whether it is a question, a change or a report, suggests questions for what is on show, shows how
 * each reply was made, and keeps any proposal pencilled until the user confirms it. Among its
 * replies are the messages it posts about issues the agents find in the day. Its header names the
 * day it answers about, the day on show, and its log marks where the conversation turned to another
 * day; three dots pulse while it thinks. The button beside an empty box listens, showing the words
 * as they are said; with words in the box it sends them. A click anywhere outside it closes it, as
 * Escape does. It stays mounted while closed so a draft and an open proposal survive.
 * @param {object} props
 * @param {boolean} props.open - Whether Ava is showing.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {string} props.topic - What is on show, for the suggested questions: a place, or `plans`.
 * @param {{id: number, text: string}|null} props.prompt - A question to put in the box when opened for one.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {() => void} props.onClose - Close Ava.
 * @param {(model: object|null, variantId?: string, changedDate?: string, actionType?: string) => Promise<void>} props.onUpdated -
 *   Refresh after a reply (with the model's status) or a confirmed change (with what changed, and its kind).
 * @param {() => void} props.onSeen - Mark Ava's messages about issues read, once its log shows them.
 * @param {() => void} props.onOpenPlans - Show today's plans, after a meal move put the set one up for review.
 * @param {(result: {notices: object[], unreadNotices: number}) => void} props.onNotices - Show the messages
 *   the agents sent back with a reply.
 */
export function TalkPanel({ open, day, today, topic, prompt, backendConnected, onClose, onUpdated, onSeen, onNotices, onOpenPlans }) {
  const { t, language } = useI18n();
  const [messages, setMessages] = useState(day.messages || []);
  const [proposals, setProposals] = useState({});
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [voiceNote, setVoiceNote] = useState("");
  // Counts requests to put focus in the box; the box takes it once Ava shows it.
  const [focusRequest, setFocusRequest] = useState(0);
  const [moved, setMoved] = useState(() => remembered(POSITION_KEY, isPosition));
  const [chosenHeight, setChosenHeight] = useState(() => remembered(HEIGHT_KEY, Number.isFinite));
  const viewport = useViewport();
  const sheetWidth = useSheetWidth();
  const panelRef = useRef(null);
  const logRef = useRef(null);
  const draftRef = useRef(null);
  const openerRef = useRef(null);
  const closeRef = useRef(onClose);
  const dragRef = useRef(null);
  const resizeRef = useRef(null);
  const dictation = useDictation(setDraft, (caught) => setVoiceNote(
    caught.name === "NotAllowedError" ? t("micDenied") : caught.message));
  const voiceReady = backendConnected && day.voice?.state === "available";
  const frame = avaFrame(viewport, moved, sheetWidth, chosenHeight ?? AVA_SIZE.height);
  const isPhone = viewport.width <= PHONE_WIDTH;
  const listening = dictation.state === "starting" || dictation.state === "listening";
  // Listening, or transcribing what was heard: the box holds Ava's words until it is idle again.
  const voiceBusy = dictation.state !== "idle";
  const hasWords = Boolean(draft.trim());
  const action = listening ? "stop" : hasWords || !voiceReady ? "send" : "speak";
  // The conversation, with the messages Ava posted about issues the agents found, in time order.
  const log = talkLog(messages, day.notices || []);
  // Ava answers about the day on show, which every message is sent with; the header names it.
  const topicName = (date) => (date === today ? t("avaTopicToday") : t("avaTopicDay", { day: shortDate(date, language) }));

  useEffect(() => setMessages(day.messages || []), [day.messages]);

  // Ava's messages count as read once its log is showing and the service can record it, which
  // clears the dot on Ava's button.
  useEffect(() => {
    if (open && backendConnected && day.unreadNotices) onSeen();
  }, [open, backendConnected, day.unreadNotices]);

  useEffect(() => {
    const element = logRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, day.notices, sending, open]);

  useEffect(() => {
    closeRef.current = onClose;
  });

  // A click anywhere outside Ava closes it, as Escape does. One that starts inside Ava, such as
  // selecting its words, keeps it open wherever it ends, and Ava's own button opens and closes it
  // itself. Listening while clicks are on their way in, any button elsewhere that opens Ava for a
  // question closes it and opens it again in the same moment, with that question.
  useEffect(() => {
    if (!open) return undefined;
    let startedInside = false;
    const inside = (target) => Boolean(panelRef.current?.contains(target));
    const onDown = (event) => {
      startedInside = inside(event.target);
    };
    const onClick = (event) => {
      if (startedInside || inside(event.target)) return;
      if (event.target instanceof Element && event.target.closest("[data-ava-toggle]")) return;
      closeRef.current();
    };
    document.addEventListener("pointerdown", onDown, true);
    document.addEventListener("click", onClick, true);
    return () => {
      document.removeEventListener("pointerdown", onDown, true);
      document.removeEventListener("click", onClick, true);
    };
  }, [open]);

  // Opening moves focus to the box; closing stops listening, discarding what was heard, and returns
  // focus to what opened Ava, unless the user has already moved on to something else.
  useEffect(() => {
    if (open) {
      openerRef.current = document.activeElement;
      setFocusRequest((count) => count + 1);
      return;
    }
    discardSpeech();
    const opener = openerRef.current;
    openerRef.current = null;
    const focusWasHere = panelRef.current?.contains(document.activeElement) || document.activeElement === document.body;
    if (opener && focusWasHere) (opener.isConnected ? opener : document.querySelector("main"))?.focus();
  }, [open]);

  // A screen that opens Ava for a particular question puts it in the box, ready to send or edit.
  useEffect(() => {
    if (!prompt) return;
    setDraft(prompt.text);
    setFocusRequest((count) => count + 1);
  }, [prompt]);

  // Runs after the render that unfolded Ava, when the box is no longer hidden and can take focus.
  useEffect(() => {
    if (focusRequest) draftRef.current?.focus();
  }, [focusRequest]);

  /**
   * Send words to Ava and show its reply, with any proposal the reply carries. The service works out
   * whether they ask, change or report.
   * @param {string} text - What the user typed, said or chose from the suggestions.
   */
  async function send(text) {
    const words = text.trim();
    if (!words || sending || !backendConnected) return;
    setDraft("");
    setVoiceNote("");
    setSending(true);
    setError("");
    const sendingId = `local-${Date.now()}`;
    setMessages((current) => [...current, { id: sendingId, role: "user", content: words, topicDate: day.date }]);
    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ date: day.date, message: words, selectedVariantId: day.selectedVariantId, language }),
      });
      // The words as saved carry their time, so they stay above the reply and any agent's message.
      setMessages((current) => [...current.map((message) => (message.id === sendingId && result.userMessage
        ? result.userMessage : message)), result.assistantMessage]);
      if (result.proposedAction) setProposals((current) => ({ ...current, [result.assistantMessage.id]: result.proposedAction }));
      // Any doubt or question an area agent sent back about this request shows under the reply.
      if (result.notices) onNotices(result);
      onUpdated(result.model);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSending(false);
    }
  }

  /** The one button beside the box: listen when it is empty, stop listening, or send its words. */
  function act() {
    if (action === "stop") {
      dictation.stop();
    } else if (action === "speak") {
      setVoiceNote("");
      dictation.start();
    } else {
      send(draft);
    }
    draftRef.current?.focus();
  }

  /** Stop listening and drop what was heard; listening only starts on an empty box, so it empties it. */
  function discardSpeech() {
    if (dictation.state === "idle") return;
    dictation.cancel();
    setDraft("");
  }

  function onPanelKey(event) {
    if (event.key !== "Escape") return;
    event.stopPropagation();
    if (voiceBusy) discardSpeech();
    else onClose();
  }

  function onDraftKey(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    if (listening) dictation.stop();
    else if (!voiceBusy) send(draft);
  }

  /** Start moving Ava by its header; its buttons and a phone-sized window keep it where it is. */
  function onDragStart(event) {
    if (event.button !== 0 || event.target.closest("button") || isPhone) return;
    dragRef.current = { x: event.clientX, y: event.clientY, left: frame.left, top: frame.top };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onDragMove(event) {
    const drag = dragRef.current;
    if (!drag) return;
    const next = avaFrame(viewport, { left: drag.left + event.clientX - drag.x, top: drag.top + event.clientY - drag.y }, 0, frame.height);
    setMoved({ left: next.left, top: next.top });
  }

  function onDragEnd() {
    if (!dragRef.current) return;
    dragRef.current = null;
    remember(POSITION_KEY, moved);
  }

  /** Put Ava back in its corner, beside any open sheet. */
  function putBack() {
    setMoved(null);
    remember(POSITION_KEY, null);
  }

  /**
   * Make Ava a given height, keeping its bottom edge where it is, as dragging its top edge does.
   * @param {number} wanted - The height asked for, kept between AVA_MIN_HEIGHT and the room above.
   * @param {{top: number, height: number}} from - Ava's frame when resizing began.
   */
  function resizeTo(wanted, from) {
    const bottom = from.top + from.height;
    const height = Math.round(Math.min(Math.max(wanted, AVA_MIN_HEIGHT), bottom - AVA_MARGIN));
    setChosenHeight(height);
    if (moved) setMoved({ left: moved.left, top: bottom - height });
    return { height, top: bottom - height };
  }

  function onResizeStart(event) {
    if (event.button !== 0) return;
    resizeRef.current = { y: event.clientY, top: frame.top, height: frame.height };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onResizeMove(event) {
    const resize = resizeRef.current;
    if (resize) resize.last = resizeTo(resize.height - (event.clientY - resize.y), resize);
  }

  function onResizeEnd() {
    const resize = resizeRef.current;
    resizeRef.current = null;
    if (!resize?.last) return;
    remember(HEIGHT_KEY, resize.last.height);
    if (moved) remember(POSITION_KEY, { left: moved.left, top: resize.last.top });
  }

  function onResizeKey(event) {
    if (event.key === "Home") {
      event.preventDefault();
      resetHeight();
      return;
    }
    const change = { ArrowUp: RESIZE_STEP, ArrowDown: -RESIZE_STEP }[event.key];
    if (!change) return;
    event.preventDefault();
    const resized = resizeTo(frame.height + change, frame);
    remember(HEIGHT_KEY, resized.height);
    if (moved) remember(POSITION_KEY, { left: moved.left, top: resized.top });
  }

  /** Give Ava its usual height again. */
  function resetHeight() {
    setChosenHeight(null);
    remember(HEIGHT_KEY, null);
  }

  const note = !backendConnected ? t("talkNeedsService")
    : listening ? t("avaListeningNote")
      : dictation.state === "finishing" ? t("voiceTranscribing") : voiceNote;
  const starters = !hasWords && !sending && !voiceBusy && backendConnected ? starterPrompts(topic) : [];

  return (
    <>
      <button type="button" className="dw-talk-scrim" hidden={!open} tabIndex={-1} aria-hidden="true" onClick={onClose} />
      <aside className="dw-talk-panel" hidden={!open} ref={panelRef}
        aria-labelledby="dw-talk-title" onKeyDown={onPanelKey}
        style={{ "--ava-left": `${frame.left}px`, "--ava-top": `${frame.top}px`, "--ava-width": `${frame.width}px`,
          "--ava-height": `${frame.height}px` }}>
        {!isPhone && (
          <div className="dw-talk-resize" role="separator" aria-orientation="horizontal" aria-label={t("avaResize")}
            aria-valuemin={AVA_MIN_HEIGHT} aria-valuemax={viewport.height - 2 * AVA_MARGIN} aria-valuenow={frame.height}
            tabIndex={0} title={t("avaResize")} onPointerDown={onResizeStart} onPointerMove={onResizeMove}
            onPointerUp={onResizeEnd} onPointerCancel={onResizeEnd} onKeyDown={onResizeKey} onDoubleClick={resetHeight} />
        )}
        <span className="dw-talk-grip" aria-hidden="true" />
        <header className="dw-talk-head" title={isPhone ? undefined : t("avaMoveHint")} onPointerDown={onDragStart}
          onPointerMove={onDragMove} onPointerUp={onDragEnd} onPointerCancel={onDragEnd} onDoubleClick={putBack}>
          <div className="dw-talk-title">
            <span className="dw-talk-avatar"><Icon name="agent" size={16} /></span>
            <h2 id="dw-talk-title">{t("navTalk")}</h2>
            <span className="dw-talk-topic" title={t("avaTopicLabel")}><Icon name="calendar" size={14} /><span>{topicName(day.date)}</span></span>
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("closeTalk")} title={t("closeTalk")} onClick={onClose}><Icon name="x" size={20} /></button>
          </div>
        </header>

        <div className="dw-talk-body">
          <div className="dw-talk-log" ref={logRef} aria-live="polite">
            {log.length === 0 && !sending && (
              <p className="dw-talk-empty"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span><span>{t("avaIntro")}</span></p>
            )}
            {log.map(({ key, message, notice, topic }) => (topic ? <p key={key} className="dw-talk-turn"><span>{topicName(topic)}</span></p>
              : notice ? <TalkNotice key={key} notice={notice} demoMode={Boolean(day.demoMode)} /> : (
              <TalkMessage key={key} message={message} demoMode={Boolean(day.demoMode)}>
                {proposals[message.id] && (
                  <ProposalCard proposal={proposals[message.id]} day={day} today={today} backendConnected={backendConnected}
                    onConfirmed={(payload, actionType) => onUpdated(null, payload.variantId, payload.date, actionType)}
                    onOpenPlans={onOpenPlans} />
                )}
              </TalkMessage>
            )))}
            {sending && (
              <p className="dw-talk-empty dw-talk-thinking" role="status"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span>
                <span>{t("consulting")}</span><span className="dw-talk-dots" aria-hidden="true"><i /><i /><i /></span></p>
            )}
            {error && <p className="dw-alert" role="alert">{error}</p>}
          </div>

          <form className="dw-talk-compose" onSubmit={(event) => { event.preventDefault(); act(); }}>
            {starters.length > 0 && (
              <div className="dw-talk-starters" role="group" aria-label={t("avaSuggestions")}>
                {starters.map((key) => (
                  <button key={key} type="button" className="dw-chip" onClick={() => { send(t(key)); draftRef.current?.focus(); }}>{t(key)}</button>
                ))}
              </div>
            )}
            <div className="dw-talk-compose-row">
              <label className="dw-visually-hidden" htmlFor="dw-talk-draft">{t("messageLabel")}</label>
              <textarea id="dw-talk-draft" ref={draftRef} rows={1} value={draft} disabled={!backendConnected} readOnly={voiceBusy}
                placeholder={listening ? t("avaListeningPlaceholder")
                  : day.date === today ? t("avaPlaceholder") : t("avaPlaceholderDay", { day: shortDate(day.date, language) })}
                aria-describedby={note ? "dw-talk-note" : undefined}
                onChange={(event) => setDraft(event.target.value)} onKeyDown={onDraftKey} />
              <button type="submit" className={`dw-button dw-talk-act${action === "send" ? " dw-button-primary" : ""}${listening ? " dw-talk-listening" : ""}`}
                aria-label={t(ACTIONS[action].label)} title={t(ACTIONS[action].label)}
                disabled={!backendConnected || sending || dictation.state === "finishing" || (action === "send" && !hasWords)}>
                <Icon name={ACTIONS[action].icon} size={18} />
              </button>
            </div>
            {note && <p id="dw-talk-note" className="dw-talk-note" role="status">{note}</p>}
          </form>
        </div>
      </aside>
    </>
  );
}
