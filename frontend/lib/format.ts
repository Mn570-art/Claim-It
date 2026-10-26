export function inr(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "Not found";
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) return String(value);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(number);
}

export function formatWhen(iso: string | null | undefined) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function statusLabel(status: string) {
  return (
    {
      draft: "Draft",
      documents_uploaded: "Documents uploaded",
      analysis_complete: "Analysis complete",
      needs_user_review: "Needs your review",
      ready_for_submission: "Ready for external submission",
    }[status] || status
  );
}
