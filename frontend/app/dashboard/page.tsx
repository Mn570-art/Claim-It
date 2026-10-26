"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Disclaimer } from "@/components/disclaimer";
import { PageIntro, PrimaryLink } from "@/components/site-header";
import { ClaimStatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { ClaimSummary } from "@/lib/types";

export default function DashboardPage() {
  const { t, language } = useI18n();
  const router = useRouter();
  const [claims, setClaims] = useState<ClaimSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    return api
      .claims()
      .then((result) => {
        setClaims(result.claims);
        setError(null);
      })
      .catch((caught) => {
        setError(caught instanceof ApiError ? caught.message : "Claims could not be loaded.");
        setClaims([]);
      });
  }

  useEffect(() => {
    let cancelled = false;
    api
      .claims()
      .then((result) => {
        if (cancelled) return;
        setClaims(result.claims);
        setError(null);
      })
      .catch((caught) => {
        if (cancelled) return;
        setError(caught instanceof ApiError ? caught.message : "Claims could not be loaded.");
        setClaims([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function openDemo() {
    setBusy(true);
    try {
      const claim = await api.seedDemo(language, "ready");
      router.push(`/claims/${claim.id}`);
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "The demo claim could not be opened.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Delete this claim and its documents from this computer?")) return;
    try {
      await api.deleteClaim(id);
      await load();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "The claim could not be deleted.");
    }
  }

  const list = claims || [];
  const review = list.filter((claim) => claim.status === "needs_user_review" || claim.status === "analysis_complete");

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <PageIntro
        eyebrow="Your claims"
        title="Claim workspace"
        body="These statuses describe preparation inside Claim-It. They are not insurer claim statuses, and nothing here has been submitted."
        action={<PrimaryLink href="/claims/new">{t.start}</PrimaryLink>}
      />
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Claims created" value={claims === null ? "…" : String(list.length)} />
        <Stat label="Needing your review" value={claims === null ? "…" : String(review.length)} />
        <Stat label="Updated most recently" value={list[0] ? formatWhen(list[0].updated_at) : "None yet"} />
      </div>
      {error ? (
        <div className="rounded-xl border border-[#f1c7d2] bg-[#fff5f7] p-4 text-sm text-[#9f1239]">
          {error}
          <button type="button" className="ml-3 underline" onClick={() => void load()}>
            Try again
          </button>
        </div>
      ) : null}
      {claims === null ? <p className="text-sm text-muted-foreground">Loading your claims…</p> : null}
      {claims && list.length === 0 && !error ? (
        <div className="rounded-xl border border-dashed border-border bg-card p-6">
          <h2 className="text-base font-medium">No claims yet</h2>
          <p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">
            Start a health claim with your own papers, or open the fictional demo. The demo uses invented people and does not call Sarvam.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <PrimaryLink href="/claims/new">{t.start}</PrimaryLink>
            <Button type="button" variant="outline" className="h-10" disabled={busy} onClick={() => void openDemo()}>
              {busy ? "Opening…" : t.demo}
            </Button>
          </div>
        </div>
      ) : null}
      <ul className="space-y-3">
        {list.map((claim) => (
          <li key={claim.id} className="rounded-xl border border-border bg-card p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs tracking-[0.14em] text-[#0f766e] uppercase">{claim.claim_reference}</p>
                <Link href={`/claims/${claim.id}`} className="font-display text-2xl text-[#122033] hover:underline">
                  {claim.nickname}
                </Link>
                <p className="mt-1 text-sm text-muted-foreground">
                  {claim.insurer_name || "Insurer not entered"} · {claim.policyholder_name || "Policyholder not entered"}
                  {claim.demo_mode ? " · Fictional demo" : ""}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Updated {formatWhen(claim.updated_at) || "just now"}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <ClaimStatusBadge status={claim.status} />
                <Button type="button" variant="ghost" size="sm" onClick={() => void remove(claim.id)}>
                  Delete
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <Disclaimer compact />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-medium">{value}</p>
    </div>
  );
}
