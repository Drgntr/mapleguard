"use client";

import { useWhaleLeaderboards } from "@/hooks/useMarketData";
import { useState } from "react";

export default function WhaleTrackerPanel() {
    const { data, isLoading, error } = useWhaleLeaderboards();
    const [activeTab, setActiveTab] = useState<"spenders" | "earners" | "farmers">("spenders");

    if (error) return <div className="text-terminal-red">Error loading whale data</div>;

    const topSpenders = data?.top_spenders || [];
    const topEarners = data?.top_earners || [];
    const topFarmers = data?.top_farmers || [];

    return (
        <div className="panel mt-6">
            <div className="panel-header flex items-center justify-between border-b border-terminal-border/50 pb-2">
                <div>
                    <span className="panel-title text-terminal-accent">WHALE TRACKER</span>
                    <span className="text-[10px] font-mono text-terminal-muted ml-2">
                        BLOCKCHAIN OWNERSHIP &amp; VOLUME
                    </span>
                </div>
                {isLoading && (
                    <span className="text-[10px] font-mono text-terminal-green animate-pulse">
                        SYNCING
                    </span>
                )}
            </div>

            <div className="p-4">
                {/* Navigation Tabs */}
                <div className="flex space-x-2 border-b border-terminal-border/30 mb-4">
                    <button
                        onClick={() => setActiveTab("spenders")}
                        className={`px-4 py-2 font-mono text-xs uppercase ${activeTab === "spenders"
                                ? "text-terminal-accent border-b-2 border-terminal-accent"
                                : "text-terminal-muted hover:text-terminal-text"
                            }`}
                    >
                        Spenders
                    </button>
                    <button
                        onClick={() => setActiveTab("earners")}
                        className={`px-4 py-2 font-mono text-xs uppercase ${activeTab === "earners"
                                ? "text-terminal-accent border-b-2 border-terminal-accent"
                                : "text-terminal-muted hover:text-terminal-text"
                            }`}
                    >
                        Earners
                    </button>
                    <button
                        onClick={() => setActiveTab("farmers")}
                        className={`px-4 py-2 font-mono text-xs uppercase ${activeTab === "farmers"
                                ? "text-terminal-accent border-b-2 border-terminal-accent"
                                : "text-terminal-muted hover:text-terminal-text"
                            }`}
                    >
                        Bot Farmers
                    </button>
                </div>

                {/* Tab Content */}
                {isLoading && !data ? (
                    <div className="py-8 text-center text-terminal-muted font-mono text-sm">
                        Calculating historical volumes...
                    </div>
                ) : (
                    <div className="grid gap-2">

                        {/* SPENDERS */}
                        {activeTab === "spenders" && (
                            <>
                                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-mono text-terminal-muted border-b border-terminal-border/30">
                                    <div className="col-span-1">RANK</div>
                                    <div className="col-span-7">WALLET</div>
                                    <div className="col-span-4 text-right">TOTAL VOLUME (NESO)</div>
                                </div>
                                {topSpenders.length === 0 ? <p className="text-xs text-terminal-muted p-3">No data</p> :
                                    topSpenders.map((w: any, index: number) => (
                                        <div key={index} className="grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-terminal-surface/50 border-b border-terminal-border/10">
                                            <div className="col-span-1 font-mono text-xs text-terminal-cyan">#{index + 1}</div>
                                            <div className="col-span-7 font-mono text-xs">{w.wallet}</div>
                                            <div className="col-span-4 text-right font-mono text-xs text-terminal-accent">{w.volume.toLocaleString()} NESO</div>
                                        </div>
                                    ))}
                            </>
                        )}

                        {/* EARNERS */}
                        {activeTab === "earners" && (
                            <>
                                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-mono text-terminal-muted border-b border-terminal-border/30">
                                    <div className="col-span-1">RANK</div>
                                    <div className="col-span-7">WALLET</div>
                                    <div className="col-span-4 text-right">TOTAL EARNINGS (NESO)</div>
                                </div>
                                {topEarners.length === 0 ? <p className="text-xs text-terminal-muted p-3">No data</p> :
                                    topEarners.map((w: any, index: number) => (
                                        <div key={index} className="grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-terminal-surface/50 border-b border-terminal-border/10">
                                            <div className="col-span-1 font-mono text-xs text-terminal-yellow">#{index + 1}</div>
                                            <div className="col-span-7 font-mono text-xs">{w.wallet}</div>
                                            <div className="col-span-4 text-right font-mono text-xs text-terminal-green">{w.volume.toLocaleString()} NESO</div>
                                        </div>
                                    ))}
                            </>
                        )}

                        {/* FARMERS */}
                        {activeTab === "farmers" && (
                            <>
                                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-mono text-terminal-muted border-b border-terminal-border/30">
                                    <div className="col-span-1">RANK</div>
                                    <div className="col-span-6">BOT WALLET</div>
                                    <div className="col-span-3 text-right">CONSOLIDATIONS</div>
                                    <div className="col-span-2 text-right">CHAR TRANSFERS</div>
                                </div>
                                {topFarmers.length === 0 ? <p className="text-xs text-terminal-muted p-3">No bot farm activity detected</p> :
                                    topFarmers.map((w: any, index: number) => (
                                        <div key={index} className="grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-terminal-surface/50 border-b border-terminal-border/10">
                                            <div className="col-span-1 font-mono text-xs text-terminal-red">#{index + 1}</div>
                                            <div className="col-span-6 font-mono text-xs">{w.wallet}</div>
                                            <div className="col-span-3 text-right font-mono text-xs text-terminal-accent">{w.consolidations} TOTAL</div>
                                            <div className="col-span-2 text-right font-mono text-xs text-terminal-yellow">{w.char_transfers || 0} CHAR</div>
                                        </div>
                                    ))}
                            </>
                        )}

                    </div>
                )}
            </div>
        </div>
    );
}
