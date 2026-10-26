"use client";

import { useState } from "react";
import type { Finding, FindingCategory } from "@/lib/types";
import { inr } from "@/lib/format";
import type { Financials } from "@/lib/types";

const FILTERS: { id: "all" | FindingCategory; label: string }[] = [
  { id: "all", label: "All findings" },
  { id: "potentially_supported", label: "Potentially supported" },
  { id: "potentially_excluded", label: "Potentially limited" },
  { id: "uncertain", label: "Uncertain" },
  { id: "missing_information", label: "Missing information" },
];

const tone: Record<string, string> = {
  potentially_supported: "bg-[#e5f3ef] text-[#0f3d38]",
  potentially_excluded: "bg-[#fde8ee] text-[#9f1239]",
  uncertain: "bg-[#f8ead2] text-[#7a4b08]",
  missing_information: "bg-[#e7eef8] text-[#1e3a5f]",
};

export function CoverageEvidenceTable({ findings }: { findings: Finding[] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const visible = findings.filter((finding) => filter === "all" || finding.category === filter);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setFilter(item.id)}
            className={`rounded-full px-3 py-1 text-xs ${filter === item.id ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground ring-1 ring-border"}`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">No findings in this filter. Run the analysis after the policy and bills are uploaded.</p>
      ) : (
        <div className="space-y-3">
          {visible.map((finding) => (
            <article key={finding.id} className="rounded-xl border border-border bg-card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs ${tone[finding.category] || ""}`}>
                  {finding.category.replaceAll("_", " ")}
                </span>
                <span className="text-xs text-muted-foreground">
                  {finding.citation_status === "verified"
                    ? `Policy text · page ${finding.source_page ?? "not stated"}`
                    : finding.citation_status === "unverified"
                      ? "Unverified — not a policy-backed conclusion"
                      : "No policy clause cited"}
                </span>
              </div>
              <h3 className="mt-2 text-base font-medium">{finding.title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{finding.explanation}</p>
              {finding.policy_clause ? (
                <blockquote className="mt-3 border-l-2 border-[#0f766e] pl-3 text-sm leading-6">
                  <span className="mb-1 block text-xs tracking-wide text-[#0f766e] uppercase">Exact policy wording</span>
                  {finding.policy_clause}
                </blockquote>
              ) : null}
              {finding.claim_evidence.length > 0 ? (
                <ul className="mt-3 space-y-1 text-sm">
                  {finding.claim_evidence.map((item) => (
                    <li key={item}>Evidence: {item}</li>
                  ))}
                </ul>
              ) : null}
              {finding.missing_information.length > 0 ? (
                <p className="mt-2 text-sm">Still needed: {finding.missing_information.join("; ")}</p>
              ) : null}
              {finding.recommended_next_step ? (
                <p className="mt-2 text-sm font-medium">Next: {finding.recommended_next_step}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function FinancialSummary({ financials }: { financials: Financials | null | undefined }) {
  if (!financials) return null;
  const rows = [
    ["Itemised total", inr(financials.itemized_total)],
    ["Printed bill total", inr(financials.printed_total)],
    ["Difference", financials.difference ? inr(financials.difference) : "None"],
    ["Amount paid, if the bill says so", inr(financials.amount_paid_documented)],
    ["Amount on the draft", inr(financials.amount_claimed)],
    ["Room rent above the printed daily limit", financials.room_rent_above_limit ? inr(financials.room_rent_above_limit) : "Not established"],
    ["Estimate", financials.estimate_label || "Unavailable"],
  ];
  return (
    <section className="rounded-xl border border-border bg-card p-4">
      <h2 className="text-base font-medium">Documented amounts</h2>
      <p className="mt-1 text-xs text-muted-foreground">These figures are calculations from the papers. They are not a reimbursement.</p>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-[#f7f3eb] px-3 py-2">
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="text-sm font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <ul className="mt-3 space-y-1 text-xs leading-5 text-muted-foreground">
        {financials.assumptions.map((item) => (
          <li key={item}>Assumption: {item}</li>
        ))}
        {financials.unresolved.map((item) => (
          <li key={item}>Unresolved: {item}</li>
        ))}
      </ul>
    </section>
  );
}
