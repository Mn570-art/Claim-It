"use client";

import { fileUrl } from "@/lib/api";
import type { ClaimDocument } from "@/lib/types";

export function DocumentViewer({ document }: { document: ClaimDocument | null }) {
  if (!document) {
    return (
      <div className="flex h-full min-h-64 items-center justify-center rounded-xl border border-dashed border-border bg-[#fffdf8] p-6 text-sm text-muted-foreground">
        Select a document to read it here. Files stay on the server and are not published as public links.
      </div>
    );
  }
  const src = fileUrl(document.file_path);
  return (
    <div className="flex h-full min-h-80 flex-col overflow-hidden rounded-xl border border-border bg-[#fffdf8]">
      <div className="border-b border-border px-3 py-2 text-xs text-muted-foreground">
        {document.original_filename}
        {document.page_count ? ` · ${document.page_count} page${document.page_count === 1 ? "" : "s"}` : ""}
      </div>
      {document.mime_type === "application/pdf" ? (
        <iframe title={document.original_filename} src={src} className="min-h-[28rem] w-full flex-1 bg-white" />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={document.original_filename} className="max-h-[32rem] w-full object-contain" />
      )}
    </div>
  );
}
