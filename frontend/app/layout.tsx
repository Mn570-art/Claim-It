import type { Metadata } from "next";
import { Newsreader, Noto_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const sans = Noto_Sans({
  subsets: ["latin", "devanagari"],
  variable: "--font-sans",
});

const display = Newsreader({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "Claim-It",
  description: "Understand your policy. Prepare your claim. In your language.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
