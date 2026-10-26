"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Disclaimer } from "@/components/disclaimer";
import { PageIntro } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const STEPS = [
  "Claim details",
  "Upload documents",
  "Narrate the incident",
  "Review extracted information",
  "Analyse the policy",
  "Review the checklist",
  "Prepare the claim draft",
];

export default function NewClaimPage() {
  const { language } = useI18n();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    nickname: "",
    insurer_name: "",
    policyholder_name: "",
    incident_date: "",
    claim_type_detail: "",
    patient_name: "",
    hospital_name: "",
  });

  function set(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit() {
    setBusy(true);
    try {
      const claim = await api.createClaim({
        claim_type: "health",
        language,
        nickname: form.nickname || null,
        insurer_name: form.insurer_name || null,
        policyholder_name: form.policyholder_name || null,
        incident_date: form.incident_date || null,
        claim_type_detail: form.claim_type_detail || null,
        patient_name: form.patient_name || null,
        hospital_name: form.hospital_name || null,
      });
      toast.success("Health claim created. Add the papers next.");
      router.push(`/claims/${claim.id}`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "The claim could not be created.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <PageIntro
        eyebrow="New health claim"
        title="Start with what you already know"
        body="Leave a field blank if you do not have it. The documents can fill some of it later, and anything still missing stays marked Not found."
      />
      <ol className="flex gap-2 overflow-x-auto pb-1">
        {STEPS.map((step, index) => (
          <li
            key={step}
            className={`rounded-full px-3 py-1.5 text-xs whitespace-nowrap ${index === 0 ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground ring-1 ring-border"}`}
          >
            {index + 1}. {step}
          </li>
        ))}
      </ol>
      <form
        className="space-y-4 rounded-xl border border-border bg-card p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Insurance type</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name="line" defaultChecked /> Health insurance
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="radio" name="line" disabled /> Motor insurance
            <span className="rounded-full bg-[#f7f3eb] px-2 py-0.5 text-xs">Future feature</span>
          </label>
        </fieldset>
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="Claim nickname" value={form.nickname} onChange={(value) => set("nickname", value)} placeholder="Father's hospitalisation" />
          <TextField label="Insurer, if known" value={form.insurer_name} onChange={(value) => set("insurer_name", value)} />
          <TextField label="Policyholder name" value={form.policyholder_name} onChange={(value) => set("policyholder_name", value)} />
          <label className="text-sm">
            <Label className="mb-1 text-xs font-normal text-muted-foreground">Incident or hospitalisation date</Label>
            <Input type="date" value={form.incident_date} onChange={(event) => set("incident_date", event.target.value)} className="h-10 bg-[#fffdf8]" />
          </label>
          <label className="text-sm">
            <Label className="mb-1 text-xs font-normal text-muted-foreground">Claim type, if applicable</Label>
            <select
              value={form.claim_type_detail}
              onChange={(event) => set("claim_type_detail", event.target.value)}
              className="h-10 w-full rounded-lg border border-input bg-[#fffdf8] px-3 text-sm"
            >
              <option value="">Not specified</option>
              <option value="reimbursement">Reimbursement</option>
              <option value="cashless">Cashless</option>
            </select>
          </label>
          <TextField label="Patient name, if different" value={form.patient_name} onChange={(value) => set("patient_name", value)} />
          <TextField label="Hospital" value={form.hospital_name} onChange={(value) => set("hospital_name", value)} />
        </div>
        <p className="text-xs text-muted-foreground">Language for this claim follows the EN / हिन्दी switch in the header.</p>
        <Button type="submit" className="h-10" disabled={busy}>
          {busy ? "Creating the claim…" : "Continue to documents"}
        </Button>
      </form>
      <Disclaimer compact />
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const id = label.toLowerCase().replace(/[^a-z]+/g, "-");
  return (
    <div className="text-sm">
      <Label htmlFor={id} className="mb-1 text-xs font-normal text-muted-foreground">
        {label}
      </Label>
      <Input id={id} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="h-10 bg-[#fffdf8]" />
    </div>
  );
}
