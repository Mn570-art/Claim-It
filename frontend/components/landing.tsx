"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Languages, ListChecks, Mic, Scale } from "lucide-react";
import { toast } from "sonner";
import { Disclaimer } from "@/components/disclaimer";
import { PageIntro, PrimaryLink } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const STEPS = [
  {
    icon: FileText,
    title: "Upload the papers",
    body: "Add the policy, discharge summary, bills, and anything else you already have. PDF and photos are accepted.",
  },
  {
    icon: Mic,
    title: "Say what happened",
    body: "Record the hospitalisation in Hindi or English, or type it. You correct the transcript before it is used.",
  },
  {
    icon: Scale,
    title: "Read the policy beside the claim",
    body: "Each finding shows the clause it came from, the page, and what is still missing. A match is not an approval.",
  },
  {
    icon: ListChecks,
    title: "Leave with a draft you can check",
    body: "Edit the summary, see the bill arithmetic, and download a PDF. You submit it to the insurer yourself.",
  },
];

export function Landing() {
  const { t, language } = useI18n();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function openDemo() {
    setBusy(true);
    try {
      const claim = await api.seedDemo(language, "ready");
      toast.success("Fictional claim opened. Sarvam was not called.");
      router.push(`/claims/${claim.id}/analysis`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The demo claim could not be opened. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:py-16">
      <PageIntro
        eyebrow="Health claim preparation"
        title={t.tagline}
        body="Claim-It helps a policyholder collect the papers, read the relevant clauses, and prepare a reimbursement draft. It does not file the claim, and it does not decide what an insurer will pay."
        action={
          <div className="flex flex-col gap-2 sm:items-end">
            <PrimaryLink href="/claims/new">{t.start}</PrimaryLink>
            <Button type="button" variant="outline" className="h-10" disabled={busy} onClick={() => void openDemo()}>
              {busy ? "Opening the fictional claim…" : t.demo}
            </Button>
          </div>
        }
      />
      {language === "hi" ? (
        <p className="mt-3 max-w-2xl text-sm text-[#0f766e]">पॉलिसी समझें। क्लेम तैयार करें। अपनी भाषा में।</p>
      ) : null}

      <section className="mt-12">
        <h2 className="font-display text-2xl text-[#122033]">{t.how}</h2>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">
          {STEPS.map((step, index) => (
            <li key={step.title} className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center gap-2 text-[#0f766e]">
                <step.icon className="size-4" />
                <span className="text-xs tracking-wide uppercase">Step {index + 1}</span>
              </div>
              <h3 className="mt-2 text-base font-medium">{step.title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-10 grid gap-3 sm:grid-cols-2">
        <article className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-[#0f766e]">
            <Languages className="size-4" />
            <h2 className="text-sm font-medium">Languages</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Hindi and English. Spoken descriptions use Sarvam Saaras when a key is configured. Short explanations can be read aloud with Bulbul. Without a key, the written screens and the labelled fictional demo still work.
          </p>
        </article>
        <article className="rounded-xl border border-border bg-card p-4">
          <h2 className="text-sm font-medium">What stays on this computer</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Uploaded files are stored for this app only. They are not published as public links. You can delete every claim from Settings. Sample people, the insurer, and the hospital in Demo mode are invented.
          </p>
        </article>
      </section>

      <div className="mt-10">
        <Disclaimer />
      </div>
    </div>
  );
}
