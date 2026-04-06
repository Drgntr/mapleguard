"use client";

import { useLiveSentinelStats, useLiveSentinelAlerts } from "@/hooks/useMarketData";

const SEVERITY_COLORS: Record<string, string> = {
    critical: "border-terminal-red text-terminal-red",
    high: "border-terminal-yellow text-terminal-yellow",
    medium: "border-terminal-accent text-terminal-accent",
    low: "border-terminal-cyan text-terminal-cyan",
};

export default function LiveSentinelPanel() {
    const { data: statsData } = useLiveSentinelStats();
    const { data: alertsData, isLoading } = useLiveSentinelAlerts(20);

    const stats = statsData || {};
    const alerts = alertsData?.alerts || [];

    return (
        <div className="space-y-4">
            {/* Mini Stats Bar */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="panel p-3">
                    <p className="stat-label">SCANS RUN</p>
                    <p className="stat-value text-terminal-cyan">{stats.scan_count || 0}</p>
                </div>
                <div className="panel p-3">
                    <p className="stat-label">TOKENS TRACKED</p>
                    <p className="stat-value text-terminal-text">{stats.tracked_tokens || 0}</p>
                </div>
                <div className="panel p-3">
                    <p className="stat-label">FLOORS INDEXED</p>
                    <p className="stat-value text-terminal-muted">{stats.floor_prices_indexed || 0}</p>
                </div>
                <div className="panel p-3">
                    <p className="stat-label">LIVE ALERTS</p>
                    <p className="stat-value text-terminal-accent">{stats.total_alerts || 0}</p>
                </div>
            </div>

            {/* Live Alerts Feed */}
            <div className="panel">
                <div className="panel-header">
                    <span className="panel-title">REAL-TIME SENTINEL ALERTS</span>
                    <span className="badge-green animate-pulse-slow">LIVE</span>
                </div>
                <div className="divide-y divide-terminal-border/50 max-h-[400px] overflow-y-auto">
                    {isLoading ? (
                        <div className="p-6 text-center text-terminal-muted font-mono text-sm">
                            Listening to live market events...
                        </div>
                    ) : alerts.length === 0 ? (
                        <div className="p-6 text-center text-terminal-muted font-mono text-sm">
                            No live anomalies detected recently.
                        </div>
                    ) : (
                        alerts.map((alert: any) => (
                            <div key={alert.id} className={`p-4 border-l-2 ${SEVERITY_COLORS[alert.severity] || "border-terminal-border"} bg-terminal-surface/50`}>
                                <div className="flex items-start justify-between mb-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="text-xs font-bold uppercase">{alert.severity}</span>
                                        <span className="text-xs text-terminal-muted">{alert.anomaly_type?.toUpperCase().replace("_", " ")}</span>
                                    </div>
                                    <span className="text-[10px] text-terminal-muted truncate ml-2">
                                        {new Date(alert.detected_at).toLocaleTimeString()}
                                    </span>
                                </div>
                                <p className="text-sm font-mono text-terminal-text mt-1">{alert.description}</p>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
