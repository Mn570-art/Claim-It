"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Disclaimer } from "@/components/disclaimer";
import { PageIntro } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Settings = {
  preferred_language: "en" | "hi";
  voice_playback: boolean;
  retention_days: number;
  sarvam_configured: boolean;
  max_upload_mb: number;
  max_pdf_pages: number;
  privacy: string;
};

export default function SettingsPage() {
  const { language, setLanguage, voice, setVoice } = useI18n();
  const router = useRouter();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .settings()
      .then((value) => {
        setSettings(value);
        setError(null);
      })
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "Settings could not be loaded."));
  }, [language, voice]);

  async function wipe() {
    setBusy(true);
    try {
      await api.deleteAll();
      toast.success("Local claim data was deleted.");
      setOpen(false);
      router.push("/");
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "The data could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <PageIntro
        eyebrow="Settings"
        title="Language, voice, and what is stored"
        body="These choices stay on this computer. The Sarvam key, if you add one, lives only in the server environment."
      />
      {error ? (
        <div className="rounded-xl border border-[#f1c7d2] bg-[#fff5f7] p-4 text-sm text-[#9f1239]">{error}</div>
      ) : null}
      <section className="space-y-3 rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-medium">Preferred language</h2>
        <p className="text-sm text-muted-foreground">Used for new claims, transcripts, and follow-up questions.</p>
        <div className="flex gap-2">
          <Button type="button" variant={language === "en" ? "default" : "outline"} className="h-10" onClick={() => setLanguage("en")}>
            English
          </Button>
          <Button type="button" variant={language === "hi" ? "default" : "outline"} className="h-10" onClick={() => setLanguage("hi")}>
            हिन्दी
          </Button>
        </div>
      </section>
      <section className="space-y-3 rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-medium">Voice playback</h2>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-1" checked={voice} onChange={(event) => setVoice(event.target.checked)} />
          <span>Offer a short spoken reading of answers when a Sarvam key is configured. The written answer always remains.</span>
        </label>
        <p className="text-xs text-muted-foreground">
          {settings?.sarvam_configured
            ? "A Sarvam key is configured on the server."
            : "No Sarvam key is configured. Demo mode and on-device reading still work. Live speech and document AI stay off."}
        </p>
      </section>
      <section className="space-y-2 rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-medium">Privacy and retention</h2>
        <p className="text-sm leading-6 text-muted-foreground">{settings?.privacy || "Loading the retention notice…"}</p>
        <p className="text-xs text-muted-foreground">
          Upload limit {settings?.max_upload_mb ?? 10} MB per file. PDF page limit {settings?.max_pdf_pages ?? 20}.
        </p>
      </section>
      <Disclaimer />
      <section className="rounded-xl border border-[#f1c7d2] bg-[#fff5f7] p-4">
        <h2 className="text-sm font-medium text-[#9f1239]">Delete all claim data</h2>
        <p className="mt-1 text-sm leading-6 text-[#9f1239]">
          Removes claims, uploaded files, transcripts, findings, and drafts stored by this app. It does not contact an insurer.
        </p>
        <Button type="button" variant="destructive" className="mt-3 h-10" onClick={() => setOpen(true)}>
          Delete all claim data
        </Button>
      </section>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete every claim on this computer?</DialogTitle>
            <DialogDescription>This cannot be undone from Claim-It. Sample files used by Demo mode are recreated the next time you open a demo.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Keep the data
            </Button>
            <Button type="button" variant="destructive" disabled={busy} onClick={() => void wipe()}>
              {busy ? "Deleting…" : "Delete all"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
