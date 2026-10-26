import { DISCLAIMER } from "@/lib/types";

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <aside className={`rounded-xl border border-[#e7d7b8] bg-[#fbf6ea] text-[#5c4a2a] ${compact ? "p-3 text-xs leading-5" : "p-4 text-sm leading-6"}`}>
      {DISCLAIMER}
    </aside>
  );
}

export function DemoBanner() {
  return (
    <div className="rounded-xl border border-[#d7c4a3] bg-[#f4ead6] px-4 py-3 text-sm text-[#5c3b12]">
      Fictional demo. These people, the insurer, and the hospital are invented. Sarvam was not called for this claim.
    </div>
  );
}
