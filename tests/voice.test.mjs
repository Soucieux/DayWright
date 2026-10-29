import assert from "node:assert/strict";
import test from "node:test";
import { MAX_VOICE_SECONDS, VOICE_RATE, beginVoiceCapture, encodeWav } from "../src/voice.js";
import { say, source } from "./interfaceText.mjs";

/** A clip of `length` seconds at one level, recorded at `rate` samples a second. */
const seconds = (length, rate = 48000) => [new Float32Array(Math.round(length * rate)).fill(0.25)];

test("a window with no microphone says so in the interface's language, as a refused one does", async () => {
  assert.equal(navigator.mediaDevices, undefined, "node, like such a window, has no microphone API");
  await assert.rejects(beginVoiceCapture(), { name: "NotSupportedError" });
  assert.match(source("talk/TalkPanel.jsx"), /const MIC_ERRORS = \{ NotAllowedError: "micDenied", NotSupportedError: "micUnavailable" \};/);
  assert.equal(say("en")("micUnavailable"), "This window can't reach a microphone.");
  assert.equal(say("zh")("micUnavailable"), "这个窗口无法使用麦克风。");
});

test("speech so far is encoded as 16 kHz mono 16-bit PCM WAV", async () => {
  const clip = encodeWav(seconds(0.5), 48000);
  const bytes = new DataView(await clip.arrayBuffer());
  /** `length` bytes of the WAV from byte `from`, as letters. */
  const text = (from, length) => String.fromCharCode(...new Uint8Array(bytes.buffer, from, length));
  assert.equal(clip.type, "audio/wav");
  assert.equal(text(0, 4), "RIFF");
  assert.equal(text(8, 4), "WAVE");
  assert.equal(bytes.getUint32(24, true), VOICE_RATE);
  assert.equal(bytes.getUint16(22, true), 1);
  assert.equal(bytes.getUint32(40, true), VOICE_RATE * 0.5 * 2);
});

test("a clip too short to hold a word gives nothing to transcribe", () => {
  assert.equal(encodeWav(seconds(0.05), 48000), null);
  assert.equal(encodeWav([], 48000), null);
});

test("a clip is cut at the longest the local transcriber takes", async () => {
  const clip = encodeWav(seconds(MAX_VOICE_SECONDS + 5), 48000);
  const bytes = new DataView(await clip.arrayBuffer());
  assert.equal(bytes.getUint32(40, true), VOICE_RATE * MAX_VOICE_SECONDS * 2);
});
