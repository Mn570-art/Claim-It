"use client";

import { CoverageEvidenceTable, FinancialSummary } from "@/components/coverage-table";
import { AnalyzeButton, DraftButton } from "@/components/claim-actions";
import { useClaim } from "@/components/claim-shell";
import { EngineNote } from "@/components/status-badge";

export default function AnalysisPage() {
  const { bundle, reload } = useClaim();
  if (!bundle) return null;
  const analysis = bundle.analysis;
  const counts = bundle.findings.reduce<Record<string, number>>((map, finding) => {
    map[finding.category] = (map[finding.category] || 0) + 1;
    return map;
  }, {});

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-[#122033]">Policy evidence</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            {analysis?.summary || "Upload the policy and the hospital papers, then run the comparison. A quoted clause is evidence to read, not a payment decision."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <AnalyzeButton claimId={bundle.id} hasDocuments={bundle.documents.length > 0} rerun={Boolean(analysis)} onDone={reload} />
          <DraftButton claimId={bundle.id} onDone={reload} />
        </div>
      </div>
      <EngineNote engine={analysis?.engine} live={analysis?.live_api_call} note={analysis?.note} />
      {analysis ? (
        <div className="grid gap-2 sm:grid-cols-4">
          <Count label="Potentially supported" value={counts.potentially_supported || 0} />
          <Count label="Potentially limited" value={counts.potentially_excluded || 0} />
          <Count label="Uncertain" value={counts.uncertain || 0} />
          <Count label="Missing information" value={counts.missing_information || 0} />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No comparison yet. The table stays empty until the policy text is checked against the claim.</p>
      )}
      {analysis && analysis.inconsistencies.length > 0 ? (
        <section className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-medium">Differences to check</h3>
          <p className="mt-1 text-xs text-muted-foreground">These are mismatches in the papers. They are not a fraud finding.</p>
          <ul className="mt-3 space-y-2 text-sm">
            {analysis.inconsistencies.map((item) => (
              <li key={`${item.type}-${item.detail}`}>
                <span className="font-medium">{item.type.replaceAll("_", " ")}</span>
                <span className="text-muted-foreground"> · {item.detail}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <FinancialSummary financials={analysis?.financials} />
      <CoverageEvidenceTable findings={bundle.findings} />
    </div>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-medium">{value}</p>
    </div>
  );
}
