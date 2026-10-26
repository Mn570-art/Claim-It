"use client";

import { useState } from "react";
import { Volume2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Citation = { quote: string; page_number: number; document_id: string };

export function AssistantPanel({
  claimId,
  language,
  demoMode,
  questions,
}: {
  claimId: string;
  language: "en" | "hi";
  demoMode: boolean;
  questions: string[];
}) {
  const { voice, sarvamConfigured } = useI18n();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [engine, setEngine] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setQuestion(trimmed);
    setBusy(true);
    try {
      const result = await api.ask(claimId, trimmed);
      setAnswer(result.answer);
      setCitations(result.citations || []);
      setEngine(result.live_api_call ? `Live Sarvam · ${result.engine}` : result.engine === "demo" ? "Demo mode · Sarvam was not called" : "Retrieved policy text · Sarvam-105B was not called");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The question could not be answered.");
    } finally {
      setBusy(false);
    }
  }

  async function speak() {
    try {
      const blob = await api.speak(answer.slice(0, 500), language);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      await audio.play();
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Playback is unavailable. The written answer stays on screen.");
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-medium">Follow-up questions</h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {demoMode
            ? "Answers in this demo quote the fictional policy. They are not a coverage decision."
            : "Answers stay tied to uploaded policy text. They are not a coverage decision."}
        </p>
      </div>
      {questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">Focused questions appear after the policy comparison, and only for facts that are still missing.</p>
      ) : (
        <ul className="space-y-2">
          {questions.map((item) => (
            <li key={item}>
              <button
                type="button"
                className="w-full rounded-lg border border-border bg-[#fffdf8] px-3 py-2 text-left text-sm hover:border-[#0f766e]"
                onClick={() => void ask(item)}
              >
                {item}
              </button>
            </li>
          ))}
        </ul>
      )}
      <Textarea
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        rows={3}
        placeholder={language === "hi" ? "पॉलिसी के बारे में प्रश्न लिखें।" : "Ask about a clause, a date, or a missing document."}
        className="min-h-20 bg-card"
      />
      <Button type="button" className="h-10" disabled={busy || !question.trim()} onClick={() => void ask(question)}>
        {busy ? "Looking at the policy…" : "Ask"}
      </Button>
      {answer ? (
        <div className="rounded-xl border border-border bg-[#fffdf8] p-3">
          {engine ? <p className="text-xs text-muted-foreground">{engine}</p> : null}
          <p className="mt-2 text-sm leading-6 whitespace-pre-wrap">{answer}</p>
          {citations.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {citations.map((citation) => (
                <li key={`${citation.page_number}-${citation.quote.slice(0, 24)}`} className="border-l-2 border-[#0f766e] pl-3 text-xs leading-5">
                  Page {citation.page_number}: {citation.quote}
                </li>
              ))}
            </ul>
          ) : null}
          {voice && sarvamConfigured ? (
            <Button type="button" variant="outline" size="sm" className="mt-3" onClick={() => void speak()}>
              <Volume2 className="size-3.5" /> Play a short reading
            </Button>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">
              {voice
                ? "Spoken playback needs a Sarvam key. The written answer stays here."
                : "Voice playback is off in Settings. The written answer stays here."}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
