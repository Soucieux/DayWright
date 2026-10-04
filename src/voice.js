/** The sample rate the local transcriber takes. */
export const VOICE_RATE = 16000;
/** The longest clip the local transcriber takes, in seconds; listening stops there. */
export const MAX_VOICE_SECONDS = 30;
/** The shortest clip worth transcribing: a tenth of a second. */
const MIN_VOICE_SAMPLES = VOICE_RATE / 10;

/**
 * Encode mono samples as the WAV the local transcriber takes: 16 kHz, 16-bit PCM, cut at
 * MAX_VOICE_SECONDS.
 * @param {Float32Array[]} chunks - The samples, in order, as recorded.
 * @param {number} rate - The rate they were recorded at.
 * @returns {Blob|null} The clip, or null when it is too short to hold a word.
 */
export function encodeWav(chunks, rate) {
  const samples = new Float32Array(chunks.reduce((length, chunk) => length + chunk.length, 0));
  let offset = 0;
  for (const chunk of chunks) {
    samples.set(chunk, offset);
    offset += chunk.length;
  }
  const count = Math.min(Math.floor(samples.length * VOICE_RATE / rate), VOICE_RATE * MAX_VOICE_SECONDS);
  if (count < MIN_VOICE_SAMPLES) return null;
  const wav = new ArrayBuffer(44 + count * 2);
  const view = new DataView(wav);
  const label = (index, value) => {
    for (let position = 0; position < value.length; position += 1) view.setUint8(index + position, value.charCodeAt(position));
  };
  label(0, "RIFF"); view.setUint32(4, 36 + count * 2, true); label(8, "WAVE");
  label(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, VOICE_RATE, true);
  view.setUint32(28, VOICE_RATE * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); label(36, "data"); view.setUint32(40, count * 2, true);
  for (let index = 0; index < count; index += 1) {
    const at = index * rate / VOICE_RATE;
    const left = Math.floor(at);
    const fraction = at - left;
    const sample = Math.max(-1, Math.min(1, samples[left] * (1 - fraction) + (samples[left + 1] ?? samples[left]) * fraction));
    view.setInt16(44 + index * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
  }
  return new Blob([wav], { type: "audio/wav" });
}

/**
 * Start listening, only after the user pressed the microphone button.
 * @returns {Promise<{seconds: () => number, snapshot: () => Blob|null, stop: () => Promise<Blob|null>}>}
 *   How long it has listened; the clip so far, for words to show while the user speaks; and
 *   stopping, which releases the microphone and gives the whole clip. A clip too short to hold a
 *   word is null.
 */
export async function beginVoiceCapture() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone access is unavailable here.");
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  let context;
  try {
    context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const silent = context.createGain();
    silent.gain.value = 0;
    const chunks = [];
    let recorded = 0;
    processor.onaudioprocess = (event) => {
      const chunk = new Float32Array(event.inputBuffer.getChannelData(0));
      chunks.push(chunk);
      recorded += chunk.length;
    };
    source.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);
    // Made after waiting for the microphone, the context can start suspended and hear nothing.
    await context.resume();
    let stopped = false;
    return {
      seconds: () => recorded / context.sampleRate,
      snapshot: () => encodeWav(chunks, context.sampleRate),
      async stop() {
        if (stopped) return null;
        stopped = true;
        processor.disconnect();
        source.disconnect();
        silent.disconnect();
        stream.getTracks().forEach((track) => track.stop());
        const rate = context.sampleRate;
        await context.close();
        return encodeWav(chunks, rate);
      },
    };
  } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    if (context) await context.close();
    throw error;
  }
}
