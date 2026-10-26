"use client";

import { ChecklistPanel } from "@/components/checklist-panel";
import { AnalyzeButton } from "@/components/claim-actions";
import { useClaim } from "@/components/claim-shell";

export default function ChecklistPage() {
  const { bundle, reload } = useClaim();
  if (!bundle) return null;
  const fromPolicy = bundle.checklist.filter((item) => item.source === "policy_requirement").length;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-[#122033]">Document checklist</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            Items marked from the policy quote a requirement that was extracted. Other rows are general suggestions, not clauses from your wording.
            {bundle.checklist.length > 0 ? ` ${fromPolicy} item${fromPolicy === 1 ? "" : "s"} come from the policy text.` : ""}
          </p>
        </div>
        {bundle.checklist.length === 0 ? (
          <AnalyzeButton claimId={bundle.id} hasDocuments={bundle.documents.length > 0} onDone={reload} />
        ) : null}
      </div>
      <ChecklistPanel claimId={bundle.id} items={bundle.checklist} onChange={reload} />
    </div>
  );
}
