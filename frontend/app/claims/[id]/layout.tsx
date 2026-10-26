import { Suspense } from "react";
import { ClaimShell } from "@/components/claim-shell";

export default function ClaimLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-4 py-6 text-sm text-muted-foreground">Opening the claim…</p>}>
      <ClaimFrame params={params}>{children}</ClaimFrame>
    </Suspense>
  );
}

async function ClaimFrame({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ClaimShell id={id}>{children}</ClaimShell>;
}
