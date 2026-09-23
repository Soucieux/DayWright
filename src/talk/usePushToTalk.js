import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { beginVoiceCapture } from "../voice";

/**
 * Push-to-talk on this Mac: record while held, transcribe locally on release, discard on cancel.
 * A release that arrives while the microphone is still starting is kept and applied once it starts.
 * @param {(text: string) => void} onText - Receives the transcript of a finished recording.
 * @param {(message: string) => void} onError - Receives why listening or transcribing failed.
 * @returns {{state: string, start: () => Promise<void>, finish: (keep: boolean) => Promise<void>}}
 *   `state` is `idle`, `starting`, `listening` or `transcribing`; `finish(true)` sends the
 *   recording to be transcribed, `finish(false)` discards it.
 */
export function usePushToTalk(onText, onError) {
  const [state, setState] = useState("idle");
  const captureRef = useRef(null);
  const releaseRef = useRef(null);

  async function start() {
    if (state !== "idle") return;
    releaseRef.current = null;
    setState("starting");
    try {
      captureRef.current = await beginVoiceCapture();
    } catch (caught) {
      setState("idle");
      onError(caught.message);
      return;
    }
    setState("listening");
    if (releaseRef.current !== null) await finish(releaseRef.current);
  }

  async function finish(keep) {
    const capture = captureRef.current;
    if (!capture) {
      releaseRef.current = keep;
      return;
    }
    captureRef.current = null;
    if (!keep) {
      setState("idle");
      capture.stop().catch(() => {});
      return;
    }
    setState("transcribing");
    try {
      const clip = await capture.stop();
      const result = await api("/api/voice/transcribe", { method: "POST", headers: { "Content-Type": "audio/wav" }, body: clip });
      if (result.text?.trim()) onText(result.text.trim());
    } catch (caught) {
      onError(caught.message);
    } finally {
      setState("idle");
    }
  }

  useEffect(() => () => captureRef.current?.stop().catch(() => {}), []);

  return { state, start, finish };
}
