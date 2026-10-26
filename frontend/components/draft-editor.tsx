"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Disclaimer } from "@/components/disclaimer";
import { ApiError, API_URL, api } from "@/lib/api";
import type { DraftPayload } from "@/lib/types";

const FIELDS: { key: keyof DraftPayload; label: string; area?: boolean }[] = [
  { key: "policyholder_name", label: "Policyholder" },
  { key: "insurer_name", label: "Insurer" },
  { key: "policy_number", label: "Policy number" },
  { key: "patient_name", label: "Patient on the bill" },
  { key: "patient_name_on_discharge", label: "Patient on the discharge summary" },
  { key: "hospital_name", label: "Hospital" },
  { key: "incident_date", label: "Incident date" },
  { key: "admission_date", label: "Admission date" },
  { key: "discharge_date", label: "Discharge date" },
  { key: "diagnosis", label: "Diagnosis as documented" },
  { key: "procedure", label: "Procedure as documented" },
  { key: "treatment", label: "Treatment as documented", area: true },
  { key: "incident_narrative", label: "Incident narrative", area: true },
  { key: "amount_claimed", label: "Amount claimed (INR)" },
  { key: "printed_total", label: "Printed bill total (INR)" },
];

export function ClaimDraftEditor({
  claimId,
  initial,
  version,
  reviewed,
  status,
  onChange,
}: {
  claimId: string;
  initial: DraftPayload;
  version: number;
  reviewed: boolean;
  status: string;
  onChange: () => Promise<void> | void;
}) {
  const [draft, setDraft] = useState(initial);
  const [seenVersion, setSeenVersion] = useState(version);
  const [busy, setBusy] = useState(false);
  const [checked, setChecked] = useState(false);

  if (version !== seenVersion) {
    setSeenVersion(version);
    setDraft(initial);
    setChecked(false);
  }

  function update(key: keyof DraftPayload, value: string) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    try {
      await action();
      toast.success(success);
      await onChange();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function copySummary() {
    const lines = [
      draft.warning,
      "",
      `Policyholder: ${draft.policyholder_name || "Not found"}`,
      `Insurer: ${draft.insurer_name || "Not found"}`,
      `Policy number: ${draft.policy_number || "Not found"}`,
      `Patient: ${draft.patient_name || "Not found"}`,
      `Hospital: ${draft.hospital_name || "Not found"}`,
      `Admission: ${draft.admission_date || "Not found"}`,
      `Discharge: ${draft.discharge_date || "Not found"}`,
      `Diagnosis: ${draft.diagnosis || "Not found"}`,
      `Amount claimed: INR ${draft.amount_claimed || "Not found"}`,
      "",
      draft.incident_narrative,
      "",
      "This draft was not submitted to an insurer.",
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
    toast.success("Summary copied.");
  }

  return (
    <div className="space-y-5">
      <Disclaimer />
      <p className="text-xs text-muted-foreground">Draft version {version}. {reviewed ? "Marked reviewed." : "Not marked reviewed yet."}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {FIELDS.map((field) => (
          <label key={field.key} className={`text-sm ${field.area ? "sm:col-span-2" : ""}`}>
            <span className="mb-1 block text-xs text-muted-foreground">{field.label}</span>
            {field.area ? (
              <Textarea value={String(draft[field.key] ?? "")} onChange={(event) => update(field.key, event.target.value)} className="min-h-28 bg-card" />
            ) : (
              <Input value={String(draft[field.key] ?? "")} onChange={(event) => update(field.key, event.target.value)} className="h-10 bg-card" />
            )}
          </label>
        ))}
      </div>
      <div>
        <h3 className="text-sm font-medium">Itemised expenses</h3>
        <div className="mt-2 space-y-2">
          {(draft.expenses || []).map((expense, index) => (
            <div key={`${expense.description}-${index}`} className="grid gap-2 sm:grid-cols-[1fr_5rem_7rem_7rem]">
              <Input
                value={expense.description}
                aria-label={`Description ${index + 1}`}
                onChange={(event) => {
                  const expenses = draft.expenses.map((item, itemIndex) => (itemIndex === index ? { ...item, description: event.target.value } : item));
                  setDraft({ ...draft, expenses });
                }}
                className="h-10 bg-card"
              />
              <Input
                value={expense.quantity}
                aria-label={`Quantity ${index + 1}`}
                onChange={(event) => {
                  const expenses = draft.expenses.map((item, itemIndex) => (itemIndex === index ? { ...item, quantity: event.target.value } : item));
                  setDraft({ ...draft, expenses });
                }}
                className="h-10 bg-card"
              />
              <Input
                value={expense.rate}
                aria-label={`Rate ${index + 1}`}
                onChange={(event) => {
                  const expenses = draft.expenses.map((item, itemIndex) => (itemIndex === index ? { ...item, rate: event.target.value } : item));
                  setDraft({ ...draft, expenses });
                }}
                className="h-10 bg-card"
              />
              <Input
                value={expense.amount}
                aria-label={`Amount ${index + 1}`}
                onChange={(event) => {
                  const expenses = draft.expenses.map((item, itemIndex) => (itemIndex === index ? { ...item, amount: event.target.value } : item));
                  setDraft({ ...draft, expenses });
                }}
                className="h-10 bg-card"
              />
            </div>
          ))}
        </div>
      </div>
      <section>
        <h3 className="text-sm font-medium">Quoted policy clauses</h3>
        <ul className="mt-2 space-y-2 text-sm">
          {(draft.policy_clauses || []).map((clause) => (
            <li key={clause.clause} className="rounded-lg bg-[#f7f3eb] p-3">
              <span className="text-xs text-muted-foreground">Page {clause.page ?? "not stated"} · {clause.origin}</span>
              <p className="mt-1">{clause.clause}</p>
            </li>
          ))}
        </ul>
      </section>
      <section className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="text-sm font-medium">Unresolved questions</h3>
          <Textarea
            className="mt-2 min-h-24 bg-card"
            value={(draft.unresolved_questions || []).join("\n")}
            onChange={(event) => setDraft({ ...draft, unresolved_questions: event.target.value.split("\n").filter(Boolean) })}
          />
        </div>
        <div>
          <h3 className="text-sm font-medium">Declarations to review</h3>
          <Textarea
            className="mt-2 min-h-24 bg-card"
            value={(draft.declarations || []).join("\n")}
            onChange={(event) => setDraft({ ...draft, declarations: event.target.value.split("\n").filter(Boolean) })}
          />
        </div>
        <div>
          <h3 className="text-sm font-medium">Supporting documents</h3>
          <Textarea
            className="mt-2 min-h-24 bg-card"
            value={(draft.supporting_documents || []).join("\n")}
            onChange={(event) => setDraft({ ...draft, supporting_documents: event.target.value.split("\n").filter(Boolean) })}
          />
        </div>
        <div>
          <h3 className="text-sm font-medium">Missing documents</h3>
          <Textarea
            className="mt-2 min-h-24 bg-card"
            value={(draft.missing_documents || []).join("\n")}
            onChange={(event) => setDraft({ ...draft, missing_documents: event.target.value.split("\n").filter(Boolean) })}
          />
        </div>
      </section>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1" checked={checked} onChange={(event) => setChecked(event.target.checked)} />
        <span>I have checked this draft. Claim-It has not sent it to an insurer, and it does not decide coverage.</span>
      </label>
      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={busy} onClick={() => run(() => api.patchDraft(claimId, draft), "Draft saved.")}>
          Save draft
        </Button>
        <Button type="button" variant="outline" disabled={busy} onClick={() => run(() => api.recalculate(claimId), "Amounts recalculated.")}>
          Recalculate
        </Button>
        <Button type="button" variant="outline" onClick={() => window.open(`${API_URL}/api/claims/${claimId}/export/pdf`, "_blank")}>
          Preview PDF
        </Button>
        <a className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm" href={`${API_URL}/api/claims/${claimId}/export/pdf`}>
          Download PDF
        </a>
        <a className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm" href={`${API_URL}/api/claims/${claimId}/export/json`}>
          Download JSON
        </a>
        <a className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm" href={`${API_URL}/api/claims/${claimId}/export/checklist.csv`}>
          Download checklist CSV
        </a>
        <Button type="button" variant="ghost" onClick={() => void copySummary()}>
          Copy summary
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={busy || !checked}
          onClick={() => run(() => api.review(claimId), "Marked reviewed. Still not submitted.")}
        >
          Mark draft reviewed
        </Button>
        <Button
          type="button"
          disabled={busy || !checked || !reviewed}
          onClick={() => run(() => api.ready(claimId), "Ready for you to submit outside Claim-It.")}
        >
          {status === "ready_for_submission" ? "Ready for external submission" : "Mark ready for external submission"}
        </Button>
      </div>
    </div>
  );
}
