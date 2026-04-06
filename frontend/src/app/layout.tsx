import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "MapleGuard | Market Sentinel",
  description:
    "Real-time market intelligence for MapleStory Universe on Henesys",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <Sidebar />
          <main className="ml-56 min-h-screen">
            <header className="h-10 border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm flex items-center px-6 sticky top-0 z-40">
              <div className="flex items-center gap-4 text-[10px] font-mono text-terminal-muted">
                <span>
                  MSU MARKET TERMINAL
                </span>
                <span className="text-terminal-border">|</span>
                <span>CHAIN: HENESYS (68414)</span>
                <span className="text-terminal-border">|</span>
                <span>TOKEN: NESO/NXPC</span>
              </div>
              <div className="ml-auto flex items-center gap-3 text-[10px] font-mono">
                <span className="text-terminal-green">LIVE</span>
                <span className="text-terminal-muted">
                  {new Date().toISOString().split("T")[0]}
                </span>
              </div>
            </header>
            <div className="p-6">{children}</div>
          </main>
        </Providers>
      </body>
    </html>
  );
}
