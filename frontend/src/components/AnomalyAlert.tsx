"use client";

import { useAnomalies } from "@/hooks/useMarketData";

const SEVERITY_ICON: Record<string, string> = {
  critical: "M12 9v2m0 4h.01",
  high: "M12 9v2m0 4h.01",
  medium: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  low: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-terminal-red",
  high: "text-terminal-yellow",
  medium: "text-terminal-accent",
  low: "text-terminal-cyan",
};

export default function AnomalyAlert() {
  const { data, isLoading } = useAnomalies(5);
  const anomalies = data?.anomalies || [];

  if (isLoading) {
    return (
      <div className="p-6 text-center text-terminal-muted font-mono text-sm">
        Scanning for anomalies...
      </div>
    );
  }

  if (anomalies.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-terminal-green/5 border border-terminal-green/20">
          <div className="w-2 h-2 rounded-full bg-terminal-green animate-pulse-slow" />
          <span className="text-sm font-mono text-terminal-green">
            ALL CLEAR - No anomalies detected
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="divide-y divide-terminal-border/50">
      {anomalies.map((alert: any, i: number) => (
        <div key={alert.id || i} className="px-4 py-3 flex items-start gap-3">
          <svg
            className={`w-4 h-4 flex-shrink-0 mt-0.5 ${SEVERITY_COLORS[alert.severity] || ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d={SEVERITY_ICON[alert.severity] || SEVERITY_ICON.low}
            />
          </svg>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-mono font-bold ${SEVERITY_COLORS[alert.severity]}`}>
                {alert.severity?.toUpperCase()}
              </span>
              <span className="text-xs font-mono text-terminal-muted">
                {alert.anomaly_type?.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>
            <p className="text-xs font-mono text-terminal-text leading-relaxed truncate">
              {alert.description}
            </p>
          </div>
          <span className="text-[10px] font-mono text-terminal-muted whitespace-nowrap">
            {alert.detected_at
              ? new Date(alert.detected_at).toLocaleTimeString()
              : ""}
          </span>
        </div>
      ))}
    </div>
  );
}
