"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

export function AnalyzeButton({
  claimId,
  hasDocuments,
  rerun = false,
  onDone,
}: {
  claimId: string;
  hasDocuments: boolean;
  rerun?: boolean;
  onDone: () => Promise<void> | void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      await api.analyze(claimId);
      toast.success("Policy comparison is ready to review. It is not an insurer decision.");
      await onDone();
      router.push(`/claims/${claimId}/analysis`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The comparison could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button type="button" className="h-10" disabled={busy || !hasDocuments} onClick={() => void run()}>
      {busy ? "Comparing the policy…" : rerun ? "Run the comparison again" : "Compare with the policy"}
    </Button>
  );
}

export function DraftButton({
  claimId,
  onDone,
}: {
  claimId: string;
  onDone: () => Promise<void> | void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      await api.draft(claimId);
      toast.success("Draft ready. Check every field before you use it.");
      await onDone();
      router.push(`/claims/${claimId}/draft`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The draft could not be prepared.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button type="button" variant="outline" className="h-10" disabled={busy} onClick={() => void run()}>
      {busy ? "Preparing the draft…" : "Prepare claim draft"}
    </Button>
  );
}
