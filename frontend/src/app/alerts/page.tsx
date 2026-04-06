"use client";

import { useState } from "react";
import {
  useLiveSentinelAlerts,
  useLiveSentinelStats,
  useHistoricalAlerts,
  useHistoricalAnalysis,
  triggerHistoricalScan,
  useSniperRanking,
} from "@/hooks/useMarketData";
import HistoricalSniperTable from "@/components/HistoricalSniperTable";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "border-terminal-red bg-terminal-red/5 text-terminal-red",
  high: "border-terminal-yellow bg-terminal-yellow/5 text-terminal-yellow",
  medium: "border-terminal-accent bg-terminal-accent/5 text-terminal-accent",
  low: "border-terminal-cyan bg-terminal-cyan/5 text-terminal-cyan",
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-terminal-red animate-pulse",
  high: "bg-terminal-yellow",
  medium: "bg-terminal-accent",
  low: "bg-terminal-cyan",
};

const TYPE_LABELS: Record<string, string> = {
  price_crash: "PRICE CRASH",
  price_spike: "PRICE SPIKE",
  rapid_relist: "RAPID RELIST",
  volume_burst: "VOLUME BURST",
  floor_break: "FLOOR BREAK",
  bot_snipe: "BOT SNIPE",
  bulk_transfer: "BULK TRANSFER",
  bot_farm_listing: "BOT FARM",
  wash_trade_history: "WASH TRADE",
  pump_and_dump: "PUMP & DUMP",
  whale_dominance: "WHALE",
  item_cornering: "CORNERING",
  dead_market: "DEAD MARKET",
  price_fixing: "PRICE FIXING",
};

function AlertCard({ alert }: { alert: any }) {
  return (
    <div className={`p-4 border-l-2 ${SEVERITY_COLORS[alert.severity] || ""}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
              alert.severity === "critical"
                ? "bg-terminal-red/20 text-terminal-red"
                : alert.severity === "high"
                ? "bg-terminal-yellow/20 text-terminal-yellow"
                : "bg-terminal-accent/20 text-terminal-accent"
            }`}
          >
            {alert.severity?.toUpperCase()}
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-terminal-surface text-terminal-text border border-terminal-border">
            {TYPE_LABELS[alert.anomaly_type] || alert.anomaly_type?.replace(/_/g, " ").toUpperCase()}
          </span>
          {alert.sentinel_type && (
            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
              alert.sentinel_type === "live"
                ? "bg-terminal-green/10 text-terminal-green border border-terminal-green/20"
                : "bg-terminal-purple/10 text-terminal-purple border border-terminal-purple/20"
            }`}>
              {alert.sentinel_type === "live" ? "LIVE" : "HIST"}
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono text-terminal-muted whitespace-nowrap ml-2">
          {alert.detected_at ? new Date(alert.detected_at).toLocaleString() : ""}
        </span>
      </div>
      <p className="text-sm font-mono text-terminal-text mb-1">
        {alert.title && <span className="font-bold">{alert.title}: </span>}
        {alert.description}
      </p>
      {alert.metadata?.wallet && (
        <span className="text-[10px] font-mono text-terminal-muted bg-terminal-surface px-2 py-0.5 rounded">
          {alert.metadata.wallet.slice(0, 8)}...{alert.metadata.wallet.slice(-4)}
        </span>
      )}
    </div>
  );
}

export default function AlertsPage() {
  const [tab, setTab] = useState<"live" | "historical" | "snipes" | "ranking">("live");
  const [scanning, setScanning] = useState(false);

  const { data: liveData } = useLiveSentinelAlerts(100);
  const { data: liveStats } = useLiveSentinelStats();
  const { data: histData } = useHistoricalAlerts(100);
  const { data: histAnalysis } = useHistoricalAnalysis();

  const liveAlerts = liveData?.alerts || [];
  const histAlerts = histData?.alerts || [];
  const ls = liveStats || {};
  const hs = histData?.stats || {};

  const handleDeepScan = async () => {
    setScanning(true);
    try {
      await triggerHistoricalScan();
    } finally {
      setTimeout(() => setScanning(false), 5000);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
            MARKET SENTINEL
          </h2>
          <p className="text-xs font-mono text-terminal-muted mt-1">
            Dual-mode anomaly detection: real-time monitoring + deep historical analysis
          </p>
        </div>
        <button
          onClick={handleDeepScan}
          disabled={scanning}
          className={`px-4 py-2 rounded text-xs font-mono font-bold transition-all ${
            scanning
              ? "bg-terminal-muted/20 text-terminal-muted cursor-not-allowed"
              : "bg-terminal-accent/20 text-terminal-accent border border-terminal-accent/30 hover:bg-terminal-accent/30"
          }`}
        >
          {scanning ? "SCANNING..." : "RUN DEEP SCAN"}
        </button>
      </div>

      {/* Combined stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        <div className="panel p-4">
          <p className="stat-label">LIVE ALERTS</p>
          <p className="stat-value text-terminal-green">{ls.total_alerts || 0}</p>
          <p className="text-[10px] font-mono text-terminal-muted mt-1">
            Scans: {ls.scan_count || 0}
          </p>
        </div>
        <div className="panel p-4">
          <p className="stat-label">HISTORICAL ALERTS</p>
          <p className="stat-value text-terminal-purple">{hs.total_alerts || 0}</p>
          <p className="text-[10px] font-mono text-terminal-muted mt-1">
            {hs.last_full_scan ? `Last: ${new Date(hs.last_full_scan).toLocaleTimeString()}` : "Pending scan"}
          </p>
        </div>
        <div className="panel p-4">
          <p className="stat-label">TRACKED TOKENS</p>
          <p className="stat-value text-terminal-cyan">{ls.tracked_tokens || 0}</p>
        </div>
        <div className="panel p-4">
          <p className="stat-label">FLOOR INDEX</p>
          <p className="stat-value text-terminal-yellow">{ls.floor_prices_indexed || 0}</p>
        </div>
        {["critical", "high"].map((sev) => {
          const liveCount = ls.by_severity?.[sev] || 0;
          const histCount = hs.by_severity?.[sev] || 0;
          const total = liveCount + histCount;
          return (
            <div key={sev} className="panel p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-2 h-2 rounded-full ${SEVERITY_DOT[sev]}`} />
                <p className="stat-label">{sev.toUpperCase()}</p>
              </div>
              <p className="text-xl font-mono font-bold">{total}</p>
            </div>
          );
        })}
      </div>

      {/* Tab selector */}
      <div className="flex gap-2 font-mono text-xs">
        <button
          onClick={() => setTab("live")}
          className={`px-4 py-2 rounded transition-all ${
            tab === "live"
              ? "bg-terminal-green/20 text-terminal-green border border-terminal-green/30"
              : "bg-terminal-surface text-terminal-muted hover:text-terminal-text border border-terminal-border"
          }`}
        >
          LIVE MONITOR
        </button>
        <button
          onClick={() => setTab("historical")}
          className={`px-4 py-2 rounded transition-all ${
            tab === "historical"
              ? "bg-terminal-purple/20 text-terminal-purple border border-terminal-purple/30"
              : "bg-terminal-surface text-terminal-muted hover:text-terminal-text border border-terminal-border"
          }`}
        >
          DEEP ANALYSIS
        </button>
        <button
          onClick={() => setTab("snipes")}
          className={`px-4 py-2 rounded transition-all ${
            tab === "snipes"
              ? "bg-terminal-red/20 text-terminal-red border border-terminal-red/30"
              : "bg-terminal-surface text-terminal-muted hover:text-terminal-text border border-terminal-border"
          }`}
        >
          SNIPER HISTORY
        </button>
        <button
          onClick={() => setTab("ranking")}
          className={`px-4 py-2 rounded transition-all ${
            tab === "ranking"
              ? "bg-terminal-yellow/20 text-terminal-yellow border border-terminal-yellow/30"
              : "bg-terminal-surface text-terminal-muted hover:text-terminal-text border border-terminal-border"
          }`}
        >
          SNIPER RANKING
        </button>
      </div>

      {/* Tab content */}
      {tab === "live" && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">LIVE ALERT FEED</span>
            <span className="text-[10px] font-mono text-terminal-green animate-pulse-slow">
              SCANNING EVERY 15s
            </span>
          </div>
          <div className="divide-y divide-terminal-border/50 max-h-[600px] overflow-y-auto">
            {liveAlerts.length === 0 ? (
              <div className="p-8 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-terminal-green/5 border border-terminal-green/20">
                  <div className="w-2 h-2 rounded-full bg-terminal-green animate-pulse-slow" />
                  <span className="text-sm font-mono text-terminal-green">
                    ALL CLEAR — No live anomalies detected
                  </span>
                </div>
                <p className="text-[10px] font-mono text-terminal-muted mt-3">
                  Monitoring recently-listed items, price anomalies, floor breaks, volume bursts, and DB order matches
                </p>
              </div>
            ) : (
              liveAlerts.map((alert: any, i: number) => (
                <AlertCard key={alert.id || i} alert={alert} />
              ))
            )}
          </div>
        </div>
      )}

      {tab === "historical" && (
        <div className="space-y-4">
          {/* Analysis summary if available */}
          {histAnalysis && histAnalysis.market_health && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="panel p-4">
                <p className="panel-title mb-2">MARKET HEALTH</p>
                <div className="space-y-1 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-terminal-muted">Liquidity Score</span>
                    <span className={
                      histAnalysis.market_health.liquidity_score > 50
                        ? "text-terminal-green"
                        : histAnalysis.market_health.liquidity_score > 20
                        ? "text-terminal-yellow"
                        : "text-terminal-red"
                    }>
                      {histAnalysis.market_health.liquidity_score}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-muted">Unique Item Types</span>
                    <span className="text-terminal-text">{histAnalysis.market_health.unique_item_types}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-muted">Single-Listing Items</span>
                    <span className="text-terminal-yellow">{histAnalysis.market_health.single_listing_types}</span>
                  </div>
                </div>
              </div>
              {histAnalysis.wallet_concentration && (
                <div className="panel p-4">
                  <p className="panel-title mb-2">WALLET CONCENTRATION</p>
                  <div className="space-y-1 text-xs font-mono">
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">HHI Index</span>
                      <span className={
                        histAnalysis.wallet_concentration.hhi_index > 2500
                          ? "text-terminal-red"
                          : "text-terminal-green"
                      }>
                        {histAnalysis.wallet_concentration.hhi_index?.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">Unique Sellers</span>
                      <span className="text-terminal-text">{histAnalysis.wallet_concentration.total_sellers}</span>
                    </div>
                    {histAnalysis.wallet_concentration.whale_wallets?.slice(0, 3).map((w: any, i: number) => (
                      <div key={i} className="flex justify-between">
                        <span className="text-terminal-muted">{w.wallet_short}</span>
                        <span className="text-terminal-yellow">{w.market_share_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {histAnalysis.price_distribution && (
                <div className="panel p-4">
                  <p className="panel-title mb-2">PRICE DISTRIBUTION</p>
                  <div className="space-y-1 text-xs font-mono">
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">Avg Price</span>
                      <span className="text-terminal-accent">{histAnalysis.price_distribution.avg_price?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">Std Dev</span>
                      <span className="text-terminal-text">{histAnalysis.price_distribution.std_dev?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">CV</span>
                      <span className="text-terminal-text">{histAnalysis.price_distribution.coefficient_of_variation}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-terminal-muted">Outliers</span>
                      <span className="text-terminal-yellow">{histAnalysis.price_distribution.outliers?.length || 0}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Historical alerts */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">HISTORICAL ALERTS</span>
              <span className="text-[10px] font-mono text-terminal-purple">
                {hs.last_full_scan ? `LAST SCAN: ${new Date(hs.last_full_scan).toLocaleString()}` : "AWAITING FIRST SCAN"}
              </span>
            </div>
            <div className="divide-y divide-terminal-border/50 max-h-[600px] overflow-y-auto">
              {histAlerts.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-terminal-muted font-mono text-sm">
                    {hs.scanning ? "Deep scan in progress..." : "No historical anomalies found. Click RUN DEEP SCAN to analyze."}
                  </p>
                </div>
              ) : (
                histAlerts.map((alert: any, i: number) => (
                  <AlertCard key={alert.id || i} alert={alert} />
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "snipes" && (
        <HistoricalSniperTable />
      )}

      {tab === "ranking" && (
        <SniperRankingTable />
      )}
    </div>
  );
}


function SniperRankingTable() {
  const { data, isLoading } = useSniperRanking(100);
  const ranking = data?.ranking || [];

  return (
    <div className="bg-terminal-surface border border-terminal-yellow/30 rounded-lg overflow-hidden relative">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-terminal-yellow to-transparent opacity-50"></div>

      <div className="p-5 border-b border-terminal-border bg-terminal-yellow/5">
        <h3 className="font-mono text-xl font-bold text-terminal-yellow flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          SNIPER WALLET RANKING
        </h3>
        <p className="text-sm font-mono text-terminal-muted mt-1">
          Wallets ranked by total snipes across the entire blockchain history.
          {data && <span className="text-terminal-yellow ml-2">{data.total_wallets} unique wallets &middot; {data.total_snipes_analyzed?.toLocaleString()} snipes analyzed</span>}
        </p>
      </div>

      <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 bg-terminal-surface z-10 shadow-sm">
            <tr className="border-b border-terminal-border bg-terminal-panel/50">
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider w-12">#</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">WALLET</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">TOTAL SNIPES</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">TOTAL SPENT</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">FLOOR VALUE</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">TOTAL SAVED</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-center">TYPES</th>
              <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">ACTIVE PERIOD</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-terminal-border/50">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="p-12 text-center text-terminal-muted font-mono text-sm">
                  Loading ranking...
                </td>
              </tr>
            ) : ranking.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-12 text-center text-terminal-muted font-mono text-sm">
                  No data available.
                </td>
              </tr>
            ) : (
              ranking.map((w: any, i: number) => {
                const medal = i === 0 ? "text-terminal-yellow" : i === 1 ? "text-terminal-text" : i === 2 ? "text-terminal-accent" : "text-terminal-muted";
                return (
                  <tr key={w.address} className="hover:bg-terminal-panel/30 transition-colors">
                    <td className={`p-4 font-mono text-sm font-bold ${medal}`}>
                      {i + 1}
                    </td>
                    <td className="p-4">
                      <a
                        href={`https://msu-explorer.xangle.io/address/${w.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-sm text-terminal-accent hover:underline"
                        title={w.address}
                      >
                        {w.address.slice(0, 8)}...{w.address.slice(-6)}
                      </a>
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-mono text-sm text-terminal-red font-bold">
                        {w.total_snipes.toLocaleString()}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="font-mono text-sm text-terminal-text">
                        {Math.round(w.total_spent).toLocaleString()}
                      </div>
                      <div className="text-[10px] text-terminal-muted font-bold tracking-widest">NESO</div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="font-mono text-sm text-terminal-green">
                        {Math.round(w.total_floor_value).toLocaleString()}
                      </div>
                      <div className="text-[10px] text-terminal-muted font-bold tracking-widest">NESO</div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="font-mono text-sm text-terminal-yellow font-bold">
                        {Math.round(w.total_saved).toLocaleString()}
                      </div>
                      <div className="text-[10px] text-terminal-muted font-bold tracking-widest">NESO</div>
                    </td>
                    <td className="p-4 text-center">
                      <div className="flex gap-1 justify-center flex-wrap">
                        {Object.entries(w.types || {}).map(([type, count]: [string, any]) => (
                          <span key={type} className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                            type.toLowerCase().includes("char")
                              ? "bg-terminal-blue/10 text-terminal-blue border-terminal-blue/30"
                              : type.toLowerCase() === "item"
                              ? "bg-terminal-cyan/10 text-terminal-cyan border-terminal-cyan/30"
                              : "bg-terminal-panel text-terminal-muted border-terminal-border"
                          }`}>
                            {type} ({count})
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="font-mono text-xs text-terminal-muted">
                        {w.first_seen ? new Date(w.first_seen).toLocaleDateString() : "—"}
                        {" → "}
                        {w.last_seen ? new Date(w.last_seen).toLocaleDateString() : "—"}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
