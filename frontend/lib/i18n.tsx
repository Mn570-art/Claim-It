"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

const copy = {
  en: {
    brand: "Claim-It",
    tagline: "Understand your policy. Prepare your claim. In your language.",
    dashboard: "Claims",
    settings: "Settings",
    start: "Start new claim",
    demo: "Open fictional demo",
    how: "How it works",
    languages: "Hindi and English",
  },
  hi: {
    brand: "Claim-It",
    tagline: "Understand your policy. Prepare your claim. In your language.",
    dashboard: "क्लेम",
    settings: "सेटिंग",
    start: "नया क्लेम शुरू करें",
    demo: "काल्पनिक डेमो खोलें",
    how: "यह कैसे काम करता है",
    languages: "हिन्दी और English",
  },
} as const;

type Language = "en" | "hi";

const I18nContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
  t: (typeof copy)[Language];
  voice: boolean;
  setVoice: (value: boolean) => void;
  sarvamConfigured: boolean | null;
} | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");
  const [voice, setVoice] = useState(true);
  const [sarvamConfigured, setSarvamConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .settings()
      .then((settings) => {
        setLanguageState(settings.preferred_language);
        setVoice(settings.voice_playback);
        setSarvamConfigured(settings.sarvam_configured);
      })
      .catch(() => setSarvamConfigured(false));
  }, []);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    api.updateSettings({ preferred_language: next }).catch(() => undefined);
  }, []);

  const setVoicePref = useCallback((next: boolean) => {
    setVoice(next);
    api.updateSettings({ voice_playback: next }).catch(() => undefined);
  }, []);

  const value = useMemo(
    () => ({ language, setLanguage, t: copy[language], voice, setVoice: setVoicePref, sarvamConfigured }),
    [language, setLanguage, voice, setVoicePref, sarvamConfigured],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("I18nProvider missing");
  return value;
}
