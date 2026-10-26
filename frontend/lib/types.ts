export type ClaimStatus =
  | "draft"
  | "documents_uploaded"
  | "analysis_complete"
  | "needs_user_review"
  | "ready_for_submission";

export type FindingCategory =
  | "potentially_supported"
  | "potentially_excluded"
  | "uncertain"
  | "missing_information";

export type ExtractedField = {
  key: string;
  label: string;
  value: string | null;
  display: string;
  source_document_id: string;
  source_filename: string;
  page_number: number | null;
  confidence: string;
  verification_status: "extracted" | "needs_review" | "not_found" | string;
};

export type LineItem = {
  description: string;
  quantity: string;
  rate: string;
  amount: string;
  page_number?: number;
};

export type ClaimDocument = {
  id: string;
  claim_id: string;
  original_filename: string;
  document_type: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  processing_status: string;
  processing_engine: string | null;
  live_api_call: boolean;
  error_message: string | null;
  extracted_fields: ExtractedField[];
  line_items: LineItem[];
  uploaded_at: string | null;
  file_path: string;
};

export type Finding = {
  id: string;
  category: FindingCategory;
  title: string;
  explanation: string;
  policy_clause: string | null;
  policy_source: string | null;
  source_document_id: string | null;
  source_page: number | null;
  claim_evidence: string[];
  missing_information: string[];
  recommended_next_step: string | null;
  citation_status: string;
  review_status: string;
};

export type ChecklistItem = {
  id: string;
  name: string;
  reason: string;
  status: "present" | "missing" | "needs_review" | "not_applicable" | string;
  source: string;
  source_reference: string | null;
  document_id: string | null;
};

export type Financials = {
  currency: string;
  itemized_total: string | null;
  printed_total: string | null;
  difference: string | null;
  amount_paid_documented: string | null;
  amount_claimed: string | null;
  documented_expense_total: string | null;
  room_rent_per_day: string | null;
  room_rent_limit_per_day: string | null;
  room_rent_above_limit: string | null;
  deductible_applied: string | null;
  copay_applied: string | null;
  estimated_reimbursement: string | null;
  estimate_status: string;
  estimate_label: string;
  assumptions: string[];
  unresolved: string[];
  duplicate_bills: { bill_number: string; note: string }[];
};

export type DraftPayload = {
  warning: string;
  fictional: boolean;
  policyholder_name: string;
  insurer_name: string;
  policy_number: string;
  patient_name: string;
  patient_name_on_discharge: string;
  hospital_name: string;
  incident_narrative: string;
  incident_date: string;
  admission_date: string;
  discharge_date: string;
  diagnosis: string;
  procedure: string;
  treatment: string;
  expenses: LineItem[];
  amount_claimed: string;
  printed_total: string;
  itemized_total: string;
  currency: string;
  financials: Financials;
  policy_clauses: { title: string; clause: string; page: number | null; category: string; origin: string }[];
  supporting_documents: string[];
  missing_documents: string[];
  unresolved_questions: string[];
  declarations: string[];
};

export type ClaimBundle = {
  id: string;
  claim_reference: string;
  claim_type: string;
  nickname: string;
  policyholder_name: string | null;
  insurer_name: string | null;
  policy_number: string | null;
  incident_date: string | null;
  claim_type_detail: string | null;
  language: "en" | "hi";
  status: ClaimStatus;
  demo_mode: boolean;
  patient_name: string | null;
  hospital_name: string | null;
  admission_date: string | null;
  discharge_date: string | null;
  created_at: string | null;
  updated_at: string | null;
  documents: ClaimDocument[];
  narrative: {
    id: string;
    transcript: string;
    confirmed_transcript: string | null;
    language: string;
    source: string;
  } | null;
  findings: Finding[];
  checklist: ChecklistItem[];
  draft: {
    id: string;
    version: number;
    reviewed_by_user: boolean;
    user_confirmed: boolean;
    draft: DraftPayload;
  } | null;
  analysis: {
    engine: string;
    live_api_call: boolean;
    summary: string;
    follow_up_questions: string[];
    inconsistencies: { type: string; severity: string; detail: string }[];
    financials: Financials;
    overall_status: string;
    note: string | null;
  } | null;
  notice?: string;
};

export type ClaimSummary = Omit<
  ClaimBundle,
  "documents" | "narrative" | "findings" | "checklist" | "draft" | "analysis"
>;

export const DISCLAIMER =
  "Claim-It provides AI-assisted document analysis and claim preparation for informational purposes. It does not determine official coverage, guarantee reimbursement, or replace advice from your insurer. Please verify all extracted information and policy interpretations before submitting a claim.";

export const DOCUMENT_TYPES = [
  ["policy", "Insurance policy"],
  ["discharge_summary", "Discharge summary"],
  ["bill", "Hospital bill or receipt"],
  ["prescription", "Prescription"],
  ["diagnostic", "Diagnostic report"],
  ["claim_form", "Claim form"],
  ["bank_proof", "Cancelled cheque or bank statement"],
  ["other", "Other support"],
] as const;
