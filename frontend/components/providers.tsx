"use client";

import { ThemeProvider } from "next-themes";
import { I18nProvider } from "@/lib/i18n";
import { SiteHeader } from "@/components/site-header";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" forcedTheme="light" enableSystem={false}>
      <I18nProvider>
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <Toaster position="top-center" />
      </I18nProvider>
    </ThemeProvider>
  );
}
