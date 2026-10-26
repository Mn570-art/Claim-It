import type { ExtractedField } from "@/lib/types";

export function ExtractedFields({ fields }: { fields: ExtractedField[] }) {
  const found = fields.filter((field) => field.verification_status !== "not_found" && field.key !== "line_items");
  const missing = fields.filter((field) => field.verification_status === "not_found");
  if (fields.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing has been extracted from this document yet.</p>;
  }
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-left text-sm">
          <thead className="text-xs text-muted-foreground">
            <tr>
              <th className="py-2 pr-3 font-medium">Field</th>
              <th className="py-2 pr-3 font-medium">Value</th>
              <th className="py-2 pr-3 font-medium">Source</th>
              <th className="py-2 font-medium">Check</th>
            </tr>
          </thead>
          <tbody>
            {found.map((field) => (
              <tr key={field.key} className="border-t border-border/80 align-top">
                <td className="py-2 pr-3">{field.label}</td>
                <td className="py-2 pr-3 font-medium">{field.display}</td>
                <td className="py-2 pr-3 text-xs text-muted-foreground">
                  {field.source_filename}
                  {field.page_number ? ` · p. ${field.page_number}` : " · page not available"}
                </td>
                <td className="py-2 text-xs">
                  {field.verification_status === "needs_review" ? "Needs review" : "Extracted"}
                  {field.confidence !== "not_available" ? ` · ${field.confidence}` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {missing.length > 0 ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">{missing.length} fields were not found</summary>
          <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
            {missing.map((field) => (
              <li key={field.key}>
                {field.label}: Not found
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
