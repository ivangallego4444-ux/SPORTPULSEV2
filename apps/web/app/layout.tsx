import type { Metadata } from "next";

import Nav from "@/components/Nav";
import PlatformFooter from "@/components/PlatformFooter";
import LeftPanel from "@/components/panels/LeftPanel";
import RightPanel from "@/components/panels/RightPanel";
import { HighlightsProvider } from "@/lib/HighlightsContext";

import "./globals.css";

export const metadata: Metadata = {
  title: "SportPulse",
  description: "Datos reales de fútbol, baloncesto y tenis, por deporte.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="bg-graphite-950 text-graphite-200 antialiased">
        <div className="mesh-background" aria-hidden />
        <HighlightsProvider>
          <Nav />
          <div className="mx-auto flex max-w-[1920px] gap-4 px-4 pt-4">
            <div className="hidden w-72 shrink-0 2xl:block">
              <LeftPanel />
            </div>
            <main className="min-h-screen min-w-0 flex-1">{children}</main>
            <div className="hidden w-72 shrink-0 2xl:block">
              <RightPanel />
            </div>
          </div>
          <PlatformFooter />
        </HighlightsProvider>
      </body>
    </html>
  );
}
