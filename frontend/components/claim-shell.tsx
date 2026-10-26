"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { ClaimBundle } from "@/lib/types";
import { ClaimStatusBadge } from "@/components/status-badge";
import { DemoBanner } from "@/components/disclaimer";

const ClaimContext = createContext<{ bundle: ClaimBundle | null; reload: () => Promise<void>; loading: boolean; error: string | null } | null>(null);

export function useClaim() {
  const value = useContext(ClaimContext);
  if (!value) throw new Error("Claim shell missing");
  return value;
}

const STEPS = [
  { href: "", label: "Workspace" },
  { href: "/analysis", label: "Policy evidence" },
  { href: "/checklist", label: "Checklist" },
  { href: "/draft", label: "Claim draft" },
];

function unlocked(bundle: ClaimBundle | null, index: number) {
  if (!bundle || index === 0) return true;
  if (index === 1) return Boolean(bundle.analysis) || bundle.documents.some((document) => document.processing_status === "completed");
  if (index === 2) return bundle.checklist.length > 0 || Boolean(bundle.analysis);
  return Boolean(bundle.draft) || Boolean(bundle.analysis);
}

export function ClaimShell({ id, children }: { id: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const [bundle, setBundle] = useState<ClaimBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  if (loadedFor !== id) {
    setLoadedFor(id);
    setBundle(null);
    setLoading(true);
    setError(null);
  }

  const reload = useCallback(async () => {
    try {
      setBundle(await api.claim(id));
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The claim could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    api
      .claim(id)
      .then((value) => {
        if (cancelled) return;
        setBundle(value);
        setError(null);
      })
      .catch((caught) => {
        if (cancelled) return;
        setError(caught instanceof ApiError ? caught.message : "The claim could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <ClaimContext.Provider value={{ bundle, reload, loading, error }}>
      <div className="mx-auto max-w-6xl space-y-4 px-4 py-6">
        {loading && !bundle ? <p className="text-sm text-muted-foreground">Opening the claim…</p> : null}
        {error ? (
          <div className="rounded-xl border border-[#f1c7d2] bg-[#fff5f7] p-4 text-sm text-[#9f1239]">
            {error}
            <button type="button" className="ml-3 underline" onClick={() => void reload()}>
              Try again
            </button>
          </div>
        ) : null}
        {bundle ? (
          <div className="space-y-4">
            {bundle.demo_mode ? <DemoBanner /> : null}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs tracking-[0.14em] text-[#0f766e] uppercase">{bundle.claim_reference}</p>
                <h1 className="font-display text-3xl text-[#122033]">{bundle.nickname}</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  {bundle.insurer_name || "Insurer not entered"} · {bundle.policyholder_name || "Policyholder not entered"}
                </p>
              </div>
              <ClaimStatusBadge status={bundle.status} />
            </div>
            <nav className="flex gap-2 overflow-x-auto pb-1">
              {STEPS.map((step, index) => {
                const href = `/claims/${id}${step.href}`;
                const active = pathname === href;
                const enabled = unlocked(bundle, index);
                return enabled ? (
                  <Link
                    key={step.href}
                    href={href}
                    className={`rounded-full px-3 py-1.5 text-sm whitespace-nowrap ${active ? "bg-primary text-primary-foreground" : "bg-card text-foreground ring-1 ring-border"}`}
                  >
                    {index + 1}. {step.label}
                  </Link>
                ) : (
                  <span key={step.href} className="rounded-full px-3 py-1.5 text-sm whitespace-nowrap text-muted-foreground ring-1 ring-border">
                    {index + 1}. {step.label}
                  </span>
                );
              })}
            </nav>
          </div>
        ) : null}
        {children}
      </div>
    </ClaimContext.Provider>
  );
}
