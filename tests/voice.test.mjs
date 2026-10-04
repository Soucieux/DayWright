import assert from "node:assert/strict";
import test from "node:test";
import { MAX_VOICE_SECONDS, VOICE_RATE, encodeWav } from "../src/voice.js";

const seconds = (length, rate = 48000) => [new Float32Array(Math.round(length * rate)).fill(0.25)];

test("speech so far is encoded as 16 kHz mono 16-bit PCM WAV", async () => {
  const clip = encodeWav(seconds(0.5), 48000);
  const bytes = new DataView(await clip.arrayBuffer());
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
