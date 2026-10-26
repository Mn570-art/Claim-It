"use client";

import { useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";

const SAMPLE = {
  en: "My father Harish Sharma was admitted to City Care Hospital, Pune on 12 October 2026 because of severe abdominal pain. He stayed for three days, had an appendectomy, and was discharged on 15 October 2026. I have uploaded the policy, the discharge summary, and the hospital bill. This is a reimbursement claim.",
  hi: "मेरे पिता हरीश शर्मा को 12 अक्टूबर 2026 को तेज पेट दर्द की वजह से सिटी केयर अस्पताल, पुणे में भर्ती किया गया। तीन दिन बाद 15 अक्टूबर को अपेंडेक्टॉमी के बाद उन्हें छुट्टी मिली। मैंने पॉलिसी, डिस्चार्ज समरी और अस्पताल का बिल अपलोड किया है। यह रीइम्बर्समेंट क्लेम है।",
};

function encodeWav(chunks: Float32Array[], sampleRate: number) {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const write = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) view.setUint8(offset + index, text.charCodeAt(index));
  };
  write(0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, length * 2, true);
  let offset = 44;
  chunks.forEach((chunk) => {
    chunk.forEach((sample) => {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
      offset += 2;
    });
  });
  return new Blob([buffer], { type: "audio/wav" });
}

export function VoiceRecorder({
  claimId,
  language,
  demoMode,
  initial,
  onSaved,
}: {
  claimId: string;
  language: "en" | "hi";
  demoMode: boolean;
  initial?: string;
  onSaved: () => Promise<void> | void;
}) {
  const [text, setText] = useState(initial || "");
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const audio = useRef<{
    context: AudioContext;
    processor: ScriptProcessorNode;
    stream: MediaStream;
    chunks: Float32Array[];
  } | null>(null);

  async function start() {
    if (demoMode) {
      toast.message("Demo mode does not send audio to Sarvam. Type the story, or insert the fictional narration.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const chunks: Float32Array[] = [];
      processor.onaudioprocess = (event) => {
        chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      const silent = context.createGain();
      silent.gain.value = 0;
      source.connect(processor);
      processor.connect(silent);
      silent.connect(context.destination);
      audio.current = { context, processor, stream, chunks };
      setRecording(true);
    } catch {
      toast.error("Microphone access was blocked. Type the incident instead.");
    }
  }

  async function stop() {
    const current = audio.current;
    if (!current) return;
    current.processor.disconnect();
    current.stream.getTracks().forEach((track) => track.stop());
    const blob = encodeWav(current.chunks, current.context.sampleRate);
    await current.context.close();
    audio.current = null;
    setRecording(false);
    setBusy(true);
    try {
      const result = await api.transcribe(claimId, blob, language);
      setText(result.transcript);
      toast.success(result.cached ? "Transcript loaded from the earlier recording." : "Transcript ready. Correct it before confirming.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Transcription failed.");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    try {
      await api.saveNarrative(claimId, { transcript: text, confirmed_transcript: text, confirm: true, language, source: recording ? "voice" : "text" });
      toast.success("Narrative saved.");
      await onSaved();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not save the narrative.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {recording ? (
          <Button type="button" variant="destructive" onClick={() => void stop()} disabled={busy}>
            <Square className="size-3.5" /> Stop and transcribe
          </Button>
        ) : (
          <Button type="button" variant="outline" onClick={() => void start()} disabled={busy}>
            <Mic className="size-3.5" /> Record in {language === "hi" ? "Hindi" : "English"}
          </Button>
        )}
        {demoMode ? (
          <Button type="button" variant="secondary" onClick={() => setText(SAMPLE[language])}>
            Insert fictional narration
          </Button>
        ) : null}
      </div>
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={6}
        placeholder={language === "hi" ? "यहाँ घटना लिखें या बोलें।" : "Describe the hospitalisation, or record it."}
        className="min-h-32 bg-card"
      />
      <Button type="button" className="h-10" onClick={() => void confirm()} disabled={busy || !text.trim()}>
        Confirm narrative
      </Button>
    </div>
  );
}
