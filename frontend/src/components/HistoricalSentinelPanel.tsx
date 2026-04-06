"use client";

import { useHistoricalAnalysis, useHistoricalAlerts } from "@/hooks/useMarketData";

export default function HistoricalSentinelPanel() {
    const { data: analysis } = useHistoricalAnalysis();
    const { data: alertsData } = useHistoricalAlerts(20);

    const alerts = alertsData?.alerts || [];

    return (
        <div className="space-y-4 mt-8">
            <div className="flex items-center justify-between">
                <h3 className="text-md font-mono font-bold text-terminal-text tracking-wider">
                    HISTORICAL DEEP SCAN
                </h3>
                <div className="flex items-center gap-2 border border-terminal-green/30 px-2 py-1 rounded bg-terminal-green/5">
                    <span className="w-2 h-2 rounded-full bg-terminal-green animate-pulse"></span>
                    <span className="text-[10px] font-mono font-bold text-terminal-green">CONTINUOUS BACKGROUND SCAN</span>
                </div>
            </div>

            {analysis?.price_distribution ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="panel p-4">
                        <p className="panel-title mb-3 text-terminal-yellow">MARKET CONCENTRATION</p>
                        <p className="text-sm font-mono text-terminal-text mb-2">
                            HHI Index: <span className="text-terminal-accent">{analysis.wallet_concentration?.hhi_index?.toLocaleString() || "N/A"}</span>
                        </p>
                        <p className="text-xs font-mono text-terminal-muted mb-4">
                            {analysis.wallet_concentration?.total_sellers} unique sellers in sample.
                        </p>

                        <p className="text-xs font-mono text-terminal-muted border-b border-terminal-border pb-1 mb-2">TOP WHALES</p>
                        {analysis.wallet_concentration?.whale_wallets?.slice(0, 3).map((w: any) => (
                            <div key={w.wallet} className="flex justify-between text-xs font-mono text-terminal-text mb-1">
                                <span>{w.wallet_short}</span>
                                <span className="text-terminal-cyan">{w.market_share_pct}% ({w.listing_count} items)</span>
                            </div>
                        ))}
                    </div>

                    <div className="panel p-4">
                        <p className="panel-title mb-3 text-terminal-red">CORNERED ITEMS</p>
                        {analysis.item_hoarding?.cornered_items?.length === 0 ? (
                            <p className="text-sm font-mono text-terminal-green">No items are cornered by a single wallet.</p>
                        ) : (
                            analysis.item_hoarding?.cornered_items?.map((item: any, i: number) => (
                                <div key={i} className="mb-2 p-2 bg-terminal-surface/30 rounded border border-terminal-border">
                                    <p className="text-sm font-bold text-terminal-text">{item.item_name}</p>
                                    <p className="text-xs text-terminal-muted mt-1">
                                        Wallet {item.wallet_short} owns <span className="text-terminal-red">{item.control_pct}%</span>
                                        ({item.owned_count}/{item.total_listed})
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            ) : (
                <div className="panel p-8 text-center text-terminal-muted font-mono text-sm border-dashed">
                    Awaiting data from continuous background deepscan...
                </div>
            )}

            {alerts.length > 0 && (
                <div className="panel">
                    <div className="panel-header">
                        <span className="panel-title">HISTORICAL ANOMALIES</span>
                    </div>
                    <div className="divide-y divide-terminal-border/50 max-h-[300px] overflow-y-auto">
                        {alerts.map((alert: any) => (
                            <div key={alert.id} className="p-4 bg-terminal-surface/20">
                                <p className="text-xs font-bold text-terminal-yellow mb-1">{alert.title || alert.anomaly_type}</p>
                                <p className="text-sm font-mono text-terminal-text">{alert.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
