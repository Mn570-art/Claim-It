"use client";

import { useState } from "react";
import { FileUp, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, uploadDocument } from "@/lib/api";
import { DOCUMENT_TYPES, type ClaimDocument } from "@/lib/types";

const ACCEPT = ".pdf,.png,.jpg,.jpeg";
const MAX = 10 * 1024 * 1024;

export function UploadZone({
  claimId,
  onUploaded,
}: {
  claimId: string;
  onUploaded: () => Promise<void> | void;
}) {
  const [type, setType] = useState("policy");
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [drag, setDrag] = useState(false);

  async function send(file: File) {
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !["pdf", "png", "jpg", "jpeg"].includes(extension)) {
      toast.error("Upload a PDF, PNG, JPG, or JPEG.");
      return;
    }
    if (file.size > MAX) {
      toast.error("Each file must be 10 MB or smaller.");
      return;
    }
    setBusy(file.name);
    setProgress(0);
    try {
      await uploadDocument(claimId, file, type, setProgress);
      toast.success(`${file.name} is ready to review.`);
      await onUploaded();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Upload failed.");
    } finally {
      setBusy(null);
      setProgress(0);
    }
  }

  return (
    <div className="space-y-3">
      <label className="block text-xs font-medium text-muted-foreground" htmlFor="document-type">
        Document type for the next upload
      </label>
      <select
        id="document-type"
        value={type}
        onChange={(event) => setType(event.target.value)}
        className="h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
      >
        {DOCUMENT_TYPES.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDrag(false);
          Array.from(event.dataTransfer.files).forEach((file) => void send(file));
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-4 py-8 text-center ${drag ? "border-[#0f766e] bg-[#e5f3ef]" : "border-[#d9cbb6] bg-[#fffdf8]"}`}
      >
        <FileUp className="mb-2 size-5 text-[#0f766e]" />
        <span className="text-sm font-medium">Drop files here, or browse</span>
        <span className="mt-1 text-xs text-muted-foreground">PDF, PNG, JPG, JPEG · 10 MB · up to 20 PDF pages</span>
        <input
          type="file"
          accept={ACCEPT}
          multiple
          className="sr-only"
          onChange={(event) => {
            Array.from(event.target.files || []).forEach((file) => void send(file));
            event.target.value = "";
          }}
        />
      </label>
      {busy ? (
        <div>
          <p className="text-xs text-muted-foreground">Reading {busy}…</p>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-[#0f766e]" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function DocumentList({
  documents,
  activeId,
  onSelect,
  onRemove,
}: {
  documents: ClaimDocument[];
  activeId?: string | null;
  onSelect: (id: string) => void;
  onRemove: (id: string) => Promise<void>;
}) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground">No documents yet.</p>;
  }
  return (
    <ul className="space-y-2">
      {documents.map((document) => (
        <li key={document.id} className={`rounded-lg border px-3 py-2 ${activeId === document.id ? "border-[#0f766e] bg-[#f3faf8]" : "border-border bg-card"}`}>
          <button type="button" className="w-full text-left" onClick={() => onSelect(document.id)}>
            <span className="block text-sm font-medium">{document.original_filename}</span>
            <span className="mt-1 block text-xs text-muted-foreground">
              {document.document_type.replaceAll("_", " ")} · {document.processing_status.replaceAll("_", " ")}
              {document.processing_engine ? ` · ${document.processing_engine}` : ""}
            </span>
          </button>
          {document.error_message ? <p className="mt-1 text-xs text-[#9f1239]">{document.error_message}</p> : null}
          <Button variant="ghost" size="sm" className="mt-1 h-7 px-2 text-xs" onClick={() => void onRemove(document.id)}>
            <Trash2 className="size-3" /> Remove
          </Button>
        </li>
      ))}
    </ul>
  );
}
