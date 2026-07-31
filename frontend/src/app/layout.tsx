import type { Metadata } from "next";
import { Fraunces, DM_Sans } from "next/font/google";
import "./globals.css";
import { SiteNav } from "@/components/SiteNav";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Agentis — multi-agent collaboration",
  description:
    "Humans and agents in one live session, with human-in-the-loop oversight that stays in the room.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} font-sans antialiased`}>
        <div className="app-shell min-h-screen text-ink">
          <SiteNav />
          {children}
        </div>
      </body>
    </html>
  );
}
