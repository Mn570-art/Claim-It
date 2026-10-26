"use client";

import { Suspense } from "react";
import { ThemeProvider } from "next-themes";
import { I18nProvider } from "@/lib/i18n";
import { SiteHeader } from "@/components/site-header";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" forcedTheme="light" enableSystem={false} enableColorScheme={false}>
      <I18nProvider>
        <Suspense fallback={<div className="h-16 border-b border-border/80 bg-[#f7f3eb]" />}>
          <SiteHeader />
        </Suspense>
        <main className="flex-1">{children}</main>
        <Toaster position="top-center" />
      </I18nProvider>
    </ThemeProvider>
  );
}
