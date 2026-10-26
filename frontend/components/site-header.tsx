"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield } from "lucide-react";
import { useI18n } from "@/lib/i18n";
export function SiteHeader() {
  const pathname = usePathname();
  const { t, language, setLanguage, sarvamConfigured } = useI18n();
  const link = (href: string, label: string) => (
    <Link
      href={href}
      className={`text-sm ${pathname === href ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}
    >
      {label}
    </Link>
  );
  return (
    <header className="sticky top-0 z-30 border-b border-border/80 bg-[#f7f3eb]/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link href="/" className="flex items-center gap-2 text-foreground">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Shield className="size-4" />
          </span>
          <span className="font-display text-xl tracking-tight">{t.brand}</span>
        </Link>
        <nav className="flex items-center gap-4">
          {link("/dashboard", t.dashboard)}
          {link("/settings", t.settings)}
          <div className="flex rounded-lg border border-border bg-card p-0.5 text-xs">
            <button
              type="button"
              className={`rounded-md px-2 py-1 ${language === "en" ? "bg-primary text-primary-foreground" : ""}`}
              onClick={() => setLanguage("en")}
            >
              EN
            </button>
            <button
              type="button"
              className={`rounded-md px-2 py-1 ${language === "hi" ? "bg-primary text-primary-foreground" : ""}`}
              onClick={() => setLanguage("hi")}
            >
              हिन्दी
            </button>
          </div>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {sarvamConfigured ? "Sarvam key on" : "Demo ready"}
          </span>
        </nav>
      </div>
    </header>
  );
}

export function PageIntro({ eyebrow, title, body, action }: { eyebrow?: string; title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="text-xs font-medium tracking-[0.16em] text-[#0f766e] uppercase">{eyebrow}</p> : null}
        <h1 className="font-display mt-1 text-3xl text-[#122033] sm:text-4xl">{title}</h1>
        {body ? <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{body}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function PrimaryLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
    >
      {children}
    </Link>
  );
}
