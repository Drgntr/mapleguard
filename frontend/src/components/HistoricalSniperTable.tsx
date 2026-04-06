"use client";

import { useState } from "react";
import { useStaticSnipes } from "@/hooks/useMarketData";

const PAGE_SIZE = 50;

export default function HistoricalSniperTable() {
    const [filter, setFilter] = useState("all");
    const [page, setPage] = useState(1);

    const { data, isLoading } = useStaticSnipes(page, PAGE_SIZE, filter);
    const snipes = data?.snipes || [];
    const totalRecords = data?.total || 0;
    const totalPages = data?.pages || 0;

    const handleFilterChange = (f: string) => {
        setFilter(f);
        setPage(1);
    };

    return (
        <div className="bg-terminal-surface border border-terminal-red/30 rounded-lg overflow-hidden relative mt-2 w-full">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-terminal-red to-transparent opacity-50"></div>

            <div className="p-5 border-b border-terminal-border flex justify-between items-center bg-terminal-red/5">
                <div>
                    <h3 className="font-mono text-xl font-bold text-terminal-red flex items-center gap-2">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        CONFIRMED SNIPER HISTORY
                    </h3>
                    <p className="text-sm font-mono text-terminal-muted mt-1 max-w-2xl">
                        Permanent record of below-floor purchases across the entire blockchain history.
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <div className="flex gap-2 font-mono text-xs">
                        {(["all", "character", "item"] as const).map((f) => {
                            const labels: Record<string, string> = { all: "ALL", character: "CHARACTERS", item: "ITEMS" };
                            const active = filter === f;
                            const colors: Record<string, string> = {
                                all: active ? "bg-terminal-red/20 text-terminal-red border border-terminal-red/30" : "",
                                character: active ? "bg-terminal-blue/20 text-terminal-blue border border-terminal-blue/30" : "",
                                item: active ? "bg-terminal-cyan/20 text-terminal-cyan border border-terminal-cyan/30" : "",
                            };
                            return (
                                <button
                                    key={f}
                                    onClick={() => handleFilterChange(f)}
                                    className={`px-3 py-1 rounded transition-colors ${active ? colors[f] : "bg-terminal-panel text-terminal-muted hover:text-terminal-text"}`}
                                >
                                    {labels[f]}
                                </button>
                            );
                        })}
                    </div>
                    <span className="px-3 py-1 rounded bg-terminal-panel text-terminal-muted border border-terminal-border text-xs font-mono">
                        {totalRecords.toLocaleString()} RECORDS
                    </span>
                </div>
            </div>

            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-terminal-surface z-10 shadow-sm">
                        <tr className="border-b border-terminal-border bg-terminal-panel/50">
                            <th className="p-2 text-xs font-mono text-terminal-muted font-bold tracking-wider w-12"></th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">TYPE</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">ASSET</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">SNIPED PRICE</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">FLOOR PRICE</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider text-right">DISCOUNT</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">SELLER / BUYER</th>
                            <th className="p-4 text-xs font-mono text-terminal-muted font-bold tracking-wider">DATE</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-terminal-border/50">
                        {isLoading ? (
                            <tr>
                                <td colSpan={8} className="p-12 text-center text-terminal-muted font-mono text-sm">
                                    Loading sniper history...
                                </td>
                            </tr>
                        ) : snipes.length === 0 ? (
                            <tr>
                                <td colSpan={8} className="p-12 text-center text-terminal-muted font-mono text-sm">
                                    NO DATA AVAILABLE. Run the scanner first.
                                </td>
                            </tr>
                        ) : (
                            snipes.map((snipe: any, i: number) => {
                                const discount = snipe.floor_price
                                    ? Math.round((1 - snipe.price / snipe.floor_price) * 100)
                                    : null;
                                return (
                                    <tr key={`${snipe.tx_hash}-${page}-${i}`} className="hover:bg-terminal-panel/30 transition-colors">
                                        <td className="p-2">
                                            <div className="w-10 h-10 rounded bg-terminal-panel border border-terminal-border overflow-hidden flex-shrink-0">
                                                {snipe.image_url ? (
                                                    <img
                                                        src={snipe.image_url}
                                                        alt={snipe.name || "NFT"}
                                                        className="w-full h-full object-contain"
                                                        loading="lazy"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = "none";
                                                        }}
                                                    />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-terminal-muted opacity-20">
                                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                        </svg>
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <span className={`px-2.5 py-1 rounded text-xs font-mono border font-bold ${
                                                (snipe.type || "").toLowerCase().includes("char")
                                                    ? "bg-terminal-blue/10 text-terminal-blue border-terminal-blue/30"
                                                    : "bg-terminal-cyan/10 text-terminal-cyan border-terminal-cyan/30"
                                            }`}>
                                                {(snipe.type || "SALE").toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="p-3">
                                            <div className="min-w-0">
                                                <div className="font-mono text-sm text-terminal-text font-bold truncate max-w-[220px]">
                                                    {snipe.name || "Unknown Asset"}
                                                </div>
                                                {snipe.token_id && (
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className="font-mono text-[11px] bg-terminal-panel border border-terminal-border px-2 py-0.5 rounded text-terminal-accent tracking-wide">
                                                            #{snipe.token_id}
                                                        </span>
                                                        {snipe.nft_url && (
                                                            <a href={snipe.nft_url} target="_blank" rel="noopener noreferrer"
                                                                className="text-[10px] font-mono text-terminal-green hover:underline">
                                                                MSU ↗
                                                            </a>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                        <td className="p-4 text-right">
                                            <div className="font-mono text-sm text-terminal-red font-bold">
                                                {snipe.price?.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                                            </div>
                                            <div className="text-[10px] text-terminal-muted font-bold tracking-widest mt-0.5">NESO</div>
                                        </td>
                                        <td className="p-4 text-right">
                                            <div className="font-mono text-sm text-terminal-green font-bold">
                                                {snipe.floor_price ? snipe.floor_price.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "—"}
                                            </div>
                                        </td>
                                        <td className="p-4 text-right">
                                            {discount !== null && (
                                                <span className={`font-mono text-sm font-bold ${
                                                    discount >= 80 ? "text-terminal-red" : discount >= 50 ? "text-terminal-yellow" : "text-terminal-accent"
                                                }`}>
                                                    -{discount}%
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            <div className="flex flex-col gap-1 font-mono text-xs">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] text-terminal-muted bg-terminal-panel px-1.5 py-0.5 rounded">SELL</span>
                                                    <span className="text-terminal-text truncate max-w-[120px]" title={snipe.seller}>
                                                        {snipe.seller ? `${snipe.seller.slice(0, 6)}...${snipe.seller.slice(-4)}` : "—"}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] text-terminal-red bg-terminal-red/10 border border-terminal-red/30 px-1.5 py-0.5 rounded">BOT</span>
                                                    <span className="text-terminal-red truncate max-w-[120px] font-bold" title={snipe.buyer}>
                                                        {snipe.buyer ? `${snipe.buyer.slice(0, 6)}...${snipe.buyer.slice(-4)}` : "—"}
                                                    </span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <div className="font-mono text-sm text-terminal-text">
                                                {snipe.date ? new Date(snipe.date).toLocaleDateString() : "—"}
                                            </div>
                                            {snipe.tx_hash && (
                                                <a
                                                    href={`https://msu-explorer.xangle.io/tx/${snipe.tx_hash}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="font-mono text-[10px] text-terminal-accent hover:underline flex items-center gap-1 mt-1"
                                                >
                                                    Xangle ↗
                                                </a>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between p-4 border-t border-terminal-border bg-terminal-panel/30">
                    <span className="text-xs font-mono text-terminal-muted">
                        Page {page} of {totalPages.toLocaleString()} ({totalRecords.toLocaleString()} total)
                    </span>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setPage(1)}
                            disabled={page <= 1}
                            className="px-3 py-1 text-xs font-mono rounded bg-terminal-surface border border-terminal-border text-terminal-muted hover:text-terminal-text disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            FIRST
                        </button>
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className="px-3 py-1 text-xs font-mono rounded bg-terminal-surface border border-terminal-border text-terminal-muted hover:text-terminal-text disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            PREV
                        </button>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="px-3 py-1 text-xs font-mono rounded bg-terminal-surface border border-terminal-border text-terminal-muted hover:text-terminal-text disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            NEXT
                        </button>
                        <button
                            onClick={() => setPage(totalPages)}
                            disabled={page >= totalPages}
                            className="px-3 py-1 text-xs font-mono rounded bg-terminal-surface border border-terminal-border text-terminal-muted hover:text-terminal-text disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            LAST
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
