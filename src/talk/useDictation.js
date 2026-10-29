import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { MAX_VOICE_SECONDS, beginVoiceCapture } from "../voice";

/** How often the words so far are transcribed while the user speaks, in milliseconds. */
const LIVE_EVERY_MS = 1500;

/**
 * Speak into Ava's box: listening starts on a press, the words so far are transcribed on this Mac
 * every LIVE_EVERY_MS and shown as the user speaks, and a second press stops listening and
 * transcribes the whole clip, which stays in the box to read over and send. Listening stops by
 * itself at MAX_VOICE_SECONDS.
 * @param {(words: string) => void} onWords - Receives the words heard so far, then all of them.
 * @param {(error: Error) => void} onError - Receives why listening or transcribing failed.
 * @returns {{state: string, start: () => Promise<void>, stop: () => Promise<void>, cancel: () => void}}
 *   `state` is `idle`, `starting`, `listening` or `finishing`; `start` begins listening, `stop` ends it and
 *   transcribes the whole clip, and `cancel` ends it and discards what was heard.
 */
export function useDictation(onWords, onError) {
  const [state, setState] = useState("idle");
  const captureRef = useRef(null);
  const timerRef = useRef(null);
  const busyRef = useRef(false);
  // Counts listening sessions, so words arriving from one that was stopped or cancelled are dropped.
  const roundRef = useRef(0);
  const handlers = useRef({ onWords, onError });
  handlers.current = { onWords, onError };

  /** The words in a WAV `clip`, transcribed on this Mac, or "" for none. */
  async function transcribe(clip) {
    const result = await api("/api/voice/transcribe", { method: "POST", headers: { "Content-Type": "audio/wav" }, body: clip });
    return result.text?.trim() || "";
  }

  /**
   * Show the words heard so far in listening session `round`; past MAX_VOICE_SECONDS stop instead. A preview still
   * being transcribed, or one that fails, is passed over.
   */
  async function hearSoFar(round) {
    const capture = captureRef.current;
    if (!capture) return;
    // The cap comes before waiting on a slow preview, so speech past it is never silently lost.
    if (capture.seconds() >= MAX_VOICE_SECONDS) {
      await stop();
      return;
    }
    if (busyRef.current) return;
    const clip = capture.snapshot();
    if (!clip) return;
    busyRef.current = true;
    try {
      const words = await transcribe(clip);
      if (words && round === roundRef.current && captureRef.current) handlers.current.onWords(words);
    } catch {
      // Words so far are a preview; the whole clip is transcribed when listening stops.
    } finally {
      busyRef.current = false;
    }
  }

  /** Start listening, a new session, and preview its words every LIVE_EVERY_MS; a refused microphone is reported. */
  async function start() {
    if (state !== "idle") return;
    const round = roundRef.current + 1;
    roundRef.current = round;
    setState("starting");
    let capture;
    try {
      capture = await beginVoiceCapture();
    } catch (caught) {
      if (round === roundRef.current) setState("idle");
      handlers.current.onError(caught);
      return;
    }
    if (round !== roundRef.current) {
      capture.stop().catch(() => {});
      return;
    }
    captureRef.current = capture;
    setState("listening");
    timerRef.current = setInterval(() => hearSoFar(round), LIVE_EVERY_MS);
  }

  /** Stop listening and pass on the whole clip's words; a failure is reported. */
  async function stop() {
    clearInterval(timerRef.current);
    const capture = captureRef.current;
    if (!capture) {
      cancel();
      return;
    }
    captureRef.current = null;
    const round = roundRef.current;
    setState("finishing");
    try {
      const clip = await capture.stop();
      const words = clip ? await transcribe(clip) : "";
      if (words && round === roundRef.current) handlers.current.onWords(words);
    } catch (caught) {
      handlers.current.onError(caught);
    } finally {
      if (round === roundRef.current) setState("idle");
    }
  }

  /** Stop listening and drop what was heard, and any words still on their way. */
  function cancel() {
    roundRef.current += 1;
    clearInterval(timerRef.current);
    captureRef.current?.stop().catch(() => {});
    captureRef.current = null;
    setState("idle");
  }

  useEffect(() => () => {
    // A capture still starting sees the new round and stops itself.
    roundRef.current += 1;
    clearInterval(timerRef.current);
    captureRef.current?.stop().catch(() => {});
  }, []);

  return { state, start, stop, cancel };
}
