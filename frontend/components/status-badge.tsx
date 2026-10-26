import { Badge } from "@/components/ui/badge";
import { statusLabel } from "@/lib/format";

const tone: Record<string, string> = {
  draft: "bg-[#ece4d6] text-[#3d4a5c]",
  documents_uploaded: "bg-[#e7eef8] text-[#1e3a5f]",
  analysis_complete: "bg-[#e5f3ef] text-[#0f3d38]",
  needs_user_review: "bg-[#f8ead2] text-[#7a4b08]",
  ready_for_submission: "bg-[#e5f0e4] text-[#1d4d32]",
};

export function ClaimStatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={`h-6 border-transparent ${tone[status] || ""}`}>
      {statusLabel(status)}
    </Badge>
  );
}

export function EngineNote({ engine, live, note }: { engine?: string | null; live?: boolean; note?: string | null }) {
  if (!engine && !note) return null;
  const label =
    engine === "sarvam_vision" || engine === "sarvam-105b" || engine === "saaras:v4"
      ? `Live Sarvam · ${engine}`
      : engine === "demo"
        ? "Demo mode · no Sarvam call"
        : engine === "local_text"
          ? "Local text extraction · Sarvam Vision was not called"
          : engine === "deterministic"
            ? live
              ? "On-device findings after a Sarvam response was rejected"
              : "On-device findings · Sarvam-105B was not called"
            : engine || "";
  return (
    <p className="text-xs leading-5 text-muted-foreground">
      <span className="font-medium text-foreground">{label}</span>
      {note ? ` ${note}` : ""}
    </p>
  );
}
