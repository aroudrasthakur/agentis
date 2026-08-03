import type { Metadata } from "next";
import { Fraunces, DM_Sans } from "next/font/google";
import "@/styles/theme.css";
import "./globals.css";
import { SiteNav } from "@/components/SiteNav";
import { AppShell } from "@/components/AppShell";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Agentis — the operating system for AI teams",
  description:
    "Humans and specialized AI agents collaborate in one persistent workspace where every action, decision, and approval remains visible.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} font-sans antialiased`}>
        <div className="app-shell min-h-screen text-ink">
          <SiteNav />
          <AppShell>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
