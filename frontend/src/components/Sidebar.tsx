"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "OVERVIEW", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4" },
  { href: "/items", label: "ITEMS", icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" },
  { href: "/characters", label: "CHARACTERS", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  { href: "/leaderboards", label: "LEADERBOARD", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
  { href: "/alerts", label: "SENTINEL", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" },
  { href: "/calculator", label: "CALCULATOR", icon: "M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" },
  { href: "/whales", label: "WHALE TRACKER", icon: "M3 3v18h18" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 h-screen fixed left-0 top-0 bg-terminal-surface border-r border-terminal-border flex flex-col z-50">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-terminal-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-terminal-accent/20 border border-terminal-accent/40 flex items-center justify-center">
            <span className="text-terminal-accent font-mono font-bold text-sm">M</span>
          </div>
          <div>
            <h1 className="text-sm font-mono font-bold text-terminal-text tracking-wider">
              MAPLEGUARD
            </h1>
            <p className="text-[10px] font-mono text-terminal-muted tracking-widest">
              MARKET SENTINEL
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-md mb-1 text-xs font-mono font-medium tracking-wider transition-all ${isActive
                ? "bg-terminal-accent/10 text-terminal-accent border border-terminal-accent/20 glow-accent"
                : "text-terminal-muted hover:text-terminal-text hover:bg-terminal-panel"
                }`}
            >
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Status footer */}
      <div className="px-4 py-3 border-t border-terminal-border">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-1.5 h-1.5 rounded-full bg-terminal-green animate-pulse-slow" />
          <span className="text-[10px] font-mono text-terminal-muted">HENESYS CHAIN</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-terminal-cyan" />
          <span className="text-[10px] font-mono text-terminal-muted">INDEXER LIVE</span>
        </div>
      </div>
    </aside>
  );
}
