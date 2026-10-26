"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DocumentList, UploadZone } from "@/components/upload-zone";
import { DocumentViewer } from "@/components/document-viewer";
import { ExtractedFields } from "@/components/extracted-fields";
import { VoiceRecorder } from "@/components/voice-recorder";
import { AssistantPanel } from "@/components/assistant-panel";
import { AnalyzeButton, DraftButton } from "@/components/claim-actions";
import { ApiError, api } from "@/lib/api";
import { inr } from "@/lib/format";
import { useClaim } from "@/components/claim-shell";

const PANELS = [
  ["documents", "Documents"],
  ["fields", "Extracted"],
  ["story", "Story"],
] as const;

export function Workspace() {
  const { bundle, reload } = useClaim();
  const [panel, setPanel] = useState<(typeof PANELS)[number][0]>("documents");
  const [seeding, setSeeding] = useState(false);
  const [saving, setSaving] = useState(false);
  const serverDetails = {
    nickname: bundle?.nickname || "",
    insurer_name: bundle?.insurer_name || "",
    policyholder_name: bundle?.policyholder_name || "",
    policy_number: bundle?.policy_number || "",
    incident_date: bundle?.incident_date || "",
    claim_type_detail: bundle?.claim_type_detail || "",
    patient_name: bundle?.patient_name || "",
    hospital_name: bundle?.hospital_name || "",
  };
  const detailsKey = bundle ? `${bundle.id}:${bundle.updated_at}` : "";
  const [detailsSource, setDetailsSource] = useState(detailsKey);
  const [details, setDetails] = useState(serverDetails);
  if (detailsSource !== detailsKey) {
    setDetailsSource(detailsKey);
    setDetails(serverDetails);
  }

  const [pickedId, setPickedId] = useState<string | null>(null);
  const activeId = bundle?.documents.some((document) => document.id === pickedId)
    ? pickedId
    : bundle?.documents[0]?.id || null;

  if (!bundle) return null;
  const claim = bundle;
  const active = claim.documents.find((document) => document.id === activeId) || null;
  const lineItems = active?.line_items || [];

  async function attachSamples() {
    setSeeding(true);
    try {
      await api.attachDemoDocuments(claim.id);
      toast.success("Fictional policy, discharge summary, bill, and pharmacy receipt are attached. Sarvam was not called.");
      await reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The sample documents could not be attached.");
    } finally {
      setSeeding(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Remove this document from the claim? The file is deleted from this computer.")) return;
    try {
      await api.deleteDocument(id);
      if (activeId === id) setPickedId(null);
      await reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The document could not be removed.");
    }
  }

  async function saveDetails() {
    setSaving(true);
    try {
      await api.updateClaim(claim.id, {
        ...details,
        claim_type_detail: details.claim_type_detail || null,
        incident_date: details.incident_date || null,
      });
      toast.success("Claim details saved.");
      await reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The details could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  const documentsPanel = (
    <div className="space-y-4">
      <h2 className="text-sm font-medium">Documents</h2>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" className="h-10" disabled={seeding} onClick={() => void attachSamples()}>
          {seeding ? "Attaching fictional papers…" : "Use fictional sample documents"}
        </Button>
      </div>
      <UploadZone claimId={bundle.id} onUploaded={reload} />
      <DocumentList documents={claim.documents} activeId={activeId} onSelect={setPickedId} onRemove={remove} />
      <DocumentViewer document={active} />
    </div>
  );

  const fieldsPanel = (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-medium">{active ? active.original_filename : "Extracted fields"}</h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Missing values stay as Not found. Nothing here is filled in from memory.
        </p>
      </div>
      <ExtractedFields fields={active?.extracted_fields || []} />
      {lineItems.length > 0 ? (
        <div className="overflow-x-auto">
          <h3 className="text-sm font-medium">Itemised lines</h3>
          <table className="mt-2 w-full min-w-[28rem] text-left text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr>
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="py-2 pr-3 font-medium">Qty</th>
                <th className="py-2 pr-3 font-medium">Rate</th>
                <th className="py-2 font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {lineItems.map((item, index) => (
                <tr key={`${item.description}-${index}`} className="border-t border-border/80">
                  <td className="py-2 pr-3">{item.description}</td>
                  <td className="py-2 pr-3">{item.quantity}</td>
                  <td className="py-2 pr-3">{inr(item.rate)}</td>
                  <td className="py-2">{inr(item.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );

  const storyPanel = (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-medium">Incident story</h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Record in Hindi or English, or type it. Correct the transcript before you confirm it.
        </p>
        <div className="mt-3">
          <VoiceRecorder
            claimId={bundle.id}
            language={bundle.language}
            demoMode={bundle.demo_mode}
            initial={bundle.narrative?.confirmed_transcript || bundle.narrative?.transcript || ""}
            onSaved={reload}
          />
        </div>
        {bundle.narrative?.confirmed_transcript ? (
          <p className="mt-2 text-xs text-[#0f766e]">Confirmed narrative is saved on this claim.</p>
        ) : null}
      </div>
      <AssistantPanel
        claimId={bundle.id}
        language={bundle.language}
        demoMode={bundle.demo_mode}
        questions={bundle.analysis?.follow_up_questions || []}
      />
    </div>
  );

  return (
    <div className="space-y-5">
      <details className="rounded-xl border border-border bg-card p-4">
        <summary className="cursor-pointer text-sm font-medium">Claim details</summary>
        <p className="mt-2 text-xs text-muted-foreground">Blank fields stay blank. Motor insurance is not available in this version.</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Claim nickname" value={details.nickname} onChange={(value) => setDetails({ ...details, nickname: value })} />
          <Field label="Insurer, if known" value={details.insurer_name} onChange={(value) => setDetails({ ...details, insurer_name: value })} />
          <Field label="Policyholder" value={details.policyholder_name} onChange={(value) => setDetails({ ...details, policyholder_name: value })} />
          <Field label="Policy number" value={details.policy_number} onChange={(value) => setDetails({ ...details, policy_number: value })} />
          <label className="text-sm">
            <span className="mb-1 block text-xs text-muted-foreground">Hospitalisation or incident date</span>
            <Input type="date" value={details.incident_date} onChange={(event) => setDetails({ ...details, incident_date: event.target.value })} className="h-10 bg-[#fffdf8]" />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs text-muted-foreground">Cashless or reimbursement</span>
            <select
              value={details.claim_type_detail}
              onChange={(event) => setDetails({ ...details, claim_type_detail: event.target.value })}
              className="h-10 w-full rounded-lg border border-input bg-[#fffdf8] px-3 text-sm"
            >
              <option value="">Not specified</option>
              <option value="reimbursement">Reimbursement</option>
              <option value="cashless">Cashless</option>
            </select>
          </label>
          <Field label="Patient, if different" value={details.patient_name} onChange={(value) => setDetails({ ...details, patient_name: value })} />
          <Field label="Hospital" value={details.hospital_name} onChange={(value) => setDetails({ ...details, hospital_name: value })} />
        </div>
        <Button type="button" className="mt-3 h-10" disabled={saving} onClick={() => void saveDetails()}>
          {saving ? "Saving…" : "Save details"}
        </Button>
      </details>

      <div className="flex gap-2 lg:hidden">
        {PANELS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setPanel(id)}
            className={`rounded-full px-3 py-1.5 text-sm ${panel === id ? "bg-primary text-primary-foreground" : "bg-card ring-1 ring-border"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,0.95fr)]">
        <section className={`rounded-xl border border-border bg-card p-4 ${panel === "documents" ? "" : "hidden lg:block"}`}>{documentsPanel}</section>
        <section className={`rounded-xl border border-border bg-card p-4 ${panel === "fields" ? "" : "hidden lg:block"}`}>{fieldsPanel}</section>
        <section className={`rounded-xl border border-border bg-card p-4 ${panel === "story" ? "" : "hidden lg:block"}`}>{storyPanel}</section>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <AnalyzeButton claimId={bundle.id} hasDocuments={bundle.documents.length > 0} rerun={Boolean(bundle.analysis)} onDone={reload} />
        <DraftButton claimId={bundle.id} onDone={reload} />
        {bundle.documents.length === 0 ? (
          <p className="text-xs text-muted-foreground">Upload a policy, or attach the fictional sample set, before comparing coverage.</p>
        ) : null}
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const id = label.toLowerCase().replace(/[^a-z]+/g, "-");
  return (
    <div className="text-sm">
      <Label htmlFor={id} className="mb-1 text-xs font-normal text-muted-foreground">
        {label}
      </Label>
      <Input id={id} value={value} onChange={(event) => onChange(event.target.value)} className="h-10 bg-[#fffdf8]" />
    </div>
  );
}
