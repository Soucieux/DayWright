/** Capture only after an explicit push-to-talk action and produce short mono PCM WAV. */
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
    processor.onaudioprocess = (event) => {
      chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);
    let stopped = false;
    return {
      async stop() {
        if (stopped) return null;
        stopped = true;
        processor.disconnect();
        source.disconnect();
        silent.disconnect();
        stream.getTracks().forEach((track) => track.stop());
        await context.close();
        const samples = new Float32Array(chunks.reduce((length, chunk) => length + chunk.length, 0));
        let offset = 0;
        for (const chunk of chunks) {
          samples.set(chunk, offset);
          offset += chunk.length;
        }
        const count = Math.floor(samples.length * 16000 / context.sampleRate);
        if (count < 1600 || count > 480000) throw new Error("Hold a brief conversation turn under 30 seconds.");
        const wav = new ArrayBuffer(44 + count * 2);
        const view = new DataView(wav);
        function label(index, value) {
          for (let position = 0; position < value.length; position += 1) view.setUint8(index + position, value.charCodeAt(position));
        }
        label(0, "RIFF"); view.setUint32(4, 36 + count * 2, true); label(8, "WAVE");
        label(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
        view.setUint16(22, 1, true); view.setUint32(24, 16000, true);
        view.setUint32(28, 32000, true); view.setUint16(32, 2, true);
        view.setUint16(34, 16, true); label(36, "data"); view.setUint32(40, count * 2, true);
        for (let index = 0; index < count; index += 1) {
          const at = index * context.sampleRate / 16000;
          const left = Math.floor(at);
          const fraction = at - left;
          const sample = Math.max(-1, Math.min(1, samples[left] * (1 - fraction) + (samples[left + 1] || samples[left]) * fraction));
          view.setInt16(44 + index * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
        }
        return new Blob([wav], { type: "audio/wav" });
      },
    };
  } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    if (context) await context.close();
    throw error;
  }
}
