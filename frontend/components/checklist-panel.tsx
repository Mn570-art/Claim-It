"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { ChecklistItem } from "@/lib/types";

const tone: Record<string, string> = {
  present: "text-[#0f766e]",
  missing: "text-[#9f1239]",
  needs_review: "text-[#9a6700]",
  not_applicable: "text-muted-foreground",
};

export function ChecklistPanel({
  claimId,
  items,
  onChange,
}: {
  claimId: string;
  items: ChecklistItem[];
  onChange: () => Promise<void> | void;
}) {
  const router = useRouter();
  async function markReviewed(name: string) {
    try {
      const bundle = await api.claim(claimId);
      const questions = bundle.analysis?.follow_up_questions || [];
      if (!bundle.draft) {
        await api.draft(claimId);
      }
      await api.patchDraft(claimId, {
        unresolved_questions: questions.filter((question) => !question.toLowerCase().includes(name.toLowerCase().split(" ")[0] || "___")),
      });
      toast.success(`${name} left on the draft for you to confirm with a file if you have one.`);
      await onChange();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not update the checklist.");
    }
  }

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">The checklist appears after the policy is analysed.</p>;
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <article key={item.id} className="rounded-xl border border-border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-medium">{item.name}</h3>
              <p className={`mt-1 text-xs font-medium uppercase tracking-wide ${tone[item.status] || ""}`}>
                {item.status.replaceAll("_", " ")}
              </p>
            </div>
            <span className="rounded-full bg-[#f7f3eb] px-2 py-1 text-xs">
              {item.source === "policy_requirement" ? "From the policy" : "General suggestion"}
              {item.source_reference ? ` · ${item.source_reference}` : ""}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.reason}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.status === "missing" ? (
              <Button type="button" size="sm" variant="outline" onClick={() => router.push(`/claims/${claimId}`)}>
                Upload
              </Button>
            ) : null}
            {item.status === "needs_review" || item.status === "missing" ? (
              <Button type="button" size="sm" variant="ghost" onClick={() => void markReviewed(item.name)}>
                Mark reviewed
              </Button>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  );
}
