"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ClaimDraftEditor } from "@/components/draft-editor";
import { useClaim } from "@/components/claim-shell";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

export default function DraftPage() {
  const { bundle, reload } = useClaim();
  const [busy, setBusy] = useState(false);
  if (!bundle) return null;
  const claim = bundle;

  async function create(regenerate: boolean) {
    setBusy(true);
    try {
      await api.draft(claim.id, regenerate);
      toast.success(regenerate ? "Draft rebuilt from the current documents." : "Draft ready. Check every field before you use it.");
      await reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The draft could not be prepared.");
    } finally {
      setBusy(false);
    }
  }

  if (!bundle.draft) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-6">
        <h2 className="font-display text-2xl text-[#122033]">Claim draft</h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
          The draft is built from extracted fields, the confirmed story, and clauses that were actually found. You will be asked to verify it before marking it ready. It is not sent anywhere.
        </p>
        <Button type="button" className="mt-4 h-10" disabled={busy} onClick={() => void create(false)}>
          {busy ? "Preparing the draft…" : "Prepare claim draft"}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-[#122033]">Claim draft</h2>
          <p className="mt-1 text-sm text-muted-foreground">Edit any field. Recalculate uses the bill lines, not a guessed settlement.</p>
        </div>
        <Button type="button" variant="outline" className="h-10" disabled={busy} onClick={() => void create(true)}>
          {busy ? "Rebuilding…" : "Rebuild from documents"}
        </Button>
      </div>
      <ClaimDraftEditor
        claimId={bundle.id}
        initial={bundle.draft.draft}
        version={bundle.draft.version}
        reviewed={bundle.draft.reviewed_by_user}
        status={bundle.status}
        onChange={reload}
      />
    </div>
  );
}
