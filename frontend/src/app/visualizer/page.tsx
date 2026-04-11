"use client";

import { useState } from "react";
import EquipmentGrid from "@/components/EquipmentGrid";

export default function VisualizerPage() {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [selectedChar, setSelectedChar] = useState<any>(null);
    const [searchError, setSearchError] = useState("");

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query) return;

        setLoading(true);
        setResults([]);
        setSelectedChar(null);
        setSearchError("");
        try {
            const res = await fetch(`/api/characters/search?query=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error(`Search failed: ${res.status}`);
            const data = await res.json();
            if (data.results && data.results.length > 0) {
                setResults(data.results);
            } else {
                setSearchError("No characters found");
            }
        } catch (err: any) {
            console.error(err);
            setSearchError(err.message || "Search failed");
        }
        setLoading(false);
    };

    const handleSelect = async (tokenId: string) => {
        setLoading(true);
        setSearchError("");
        try {
            const res = await fetch(`/api/characters/${encodeURIComponent(tokenId)}/detail`);
            if (!res.ok) throw new Error(`Detail failed: ${res.status}`);
            const data = await res.json();
            if (data.character) {
                setSelectedChar(data.character);
            } else {
                setSearchError("Character data not available");
            }
        } catch (err: any) {
            console.error(err);
            setSearchError(err.message || "Failed to load character");
        }
        setLoading(false);
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
            <div className="flex items-end justify-between border-b border-terminal-border pb-4">
                <div>
                    <h1 className="text-2xl font-mono font-bold text-terminal-text tracking-tight flex items-center gap-3">
                        <svg className="w-6 h-6 text-terminal-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        CHARACTER VISUALIZER
                    </h1>
                    <p className="text-xs font-mono text-terminal-muted mt-2 max-w-2xl">
                        Search for characters by nickname or wallet address to inspect their full equipment layout and stats.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Search Panel */}
                <div className="lg:col-span-1 space-y-4">
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <input
                                type="text"
                                placeholder="Nickname or CHAR..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                disabled={loading}
                                className={`w-full bg-terminal-surface border pl-10 pr-3 py-2 rounded text-xs font-mono text-terminal-text outline-none transition-all ${
                                    loading
                                        ? "border-terminal-cyan/50 opacity-60 cursor-not-allowed"
                                        : "border-terminal-border focus:border-terminal-cyan"
                                }`}
                            />
                            <svg className="w-4 h-4 text-terminal-muted absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className={`flex items-center gap-2 border px-4 py-2 rounded text-xs font-mono font-bold transition-all ${
                                loading
                                    ? "bg-terminal-cyan/30 border-terminal-cyan text-terminal-cyan animate-pulse shadow-[0_0_15px_rgba(var(--terminal-cyan),0.4)]"
                                    : "bg-terminal-cyan/20 hover:bg-terminal-cyan/30 text-terminal-cyan border-terminal-cyan/50 disabled:opacity-50"
                            }`}
                        >
                            {loading && (
                                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                            )}
                            {loading ? "SEARCHING..." : "SEARCH"}
                        </button>
                    </form>

                    {loading && !selectedChar && (
                        <div className="p-6 flex flex-col items-center gap-3 bg-terminal-panel border border-terminal-cyan/30 rounded-lg shadow-[0_0_20px_rgba(var(--terminal-cyan),0.1)]">
                            <div className="relative w-10 h-10">
                                <div className="absolute inset-0 border-2 border-terminal-cyan/20 rounded-full" />
                                <div className="absolute inset-0 border-2 border-transparent border-t-terminal-cyan rounded-full animate-spin" />
                            </div>
                            <div className="text-xs font-mono text-terminal-cyan font-bold tracking-wider animate-pulse">
                                SCANNING REGISTRY...
                            </div>
                            <div className="w-full bg-terminal-surface rounded-full h-1 overflow-hidden">
                                <div className="h-full bg-terminal-cyan/60 rounded-full animate-[loading_1.5s_ease-in-out_infinite]" style={{ width: '60%', animation: 'loading 1.5s ease-in-out infinite' }} />
                            </div>
                        </div>
                    )}

                    {searchError && !loading && (
                        <div className="p-4 text-center bg-terminal-panel border border-terminal-red/30 rounded-lg">
                            <div className="text-xs font-mono text-terminal-red font-bold">{searchError}</div>
                        </div>
                    )}

                    {results.length > 0 && !selectedChar && (
                        <div className="bg-terminal-panel border border-terminal-border rounded-lg overflow-hidden">
                            <div className="bg-terminal-surface/50 border-b border-terminal-border px-3 py-2 text-[10px] font-mono text-terminal-muted">
                                {results.length} MATCHES FOUND
                            </div>
                            <ul className="divide-y divide-terminal-border/50">
                                {results.map((r, i) => (
                                    <li
                                        key={i}
                                        onClick={() => handleSelect(r.token_id)}
                                        className="p-3 hover:bg-terminal-surface/80 cursor-pointer transition-colors"
                                    >
                                        <div className="font-mono text-sm text-terminal-text font-bold">{r.name}</div>
                                        <div className="font-mono text-[10px] text-terminal-muted mt-1">{r.class_name} - Lv.{r.level}</div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                {/* Visualizer Panel */}
                <div className="lg:col-span-3">
                    {loading && selectedChar && (
                        <div className="h-96 flex flex-col items-center justify-center gap-4">
                            <div className="relative w-12 h-12">
                                <div className="absolute inset-0 border-2 border-terminal-cyan/20 rounded-full" />
                                <div className="absolute inset-0 border-2 border-transparent border-t-terminal-cyan rounded-full animate-spin" />
                                <div className="absolute inset-2 border-2 border-transparent border-b-terminal-cyan/60 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
                            </div>
                            <div className="text-sm font-mono text-terminal-cyan font-bold tracking-wider animate-pulse">
                                DECODING CHARACTER DATA...
                            </div>
                        </div>
                    )}

                    {selectedChar && !loading && (
                        <div className="bg-terminal-panel border border-terminal-border rounded-lg overflow-hidden flex flex-col md:flex-row shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
                            {/* Profile Header Side */}
                            <div className="p-6 border-b md:border-b-0 md:border-r border-terminal-border flex flex-col items-center justify-center min-w-[250px] bg-terminal-surface/30">
                                <div className="w-24 h-24 rounded-full border-2 border-terminal-cyan/50 overflow-hidden mb-4 shadow-[0_0_15px_rgba(var(--terminal-cyan),0.2)] bg-terminal-panel flex items-center justify-center">
                                    {selectedChar.image_url ? (
                                        <img src={selectedChar.image_url} alt={selectedChar.name} className="w-full h-full object-cover" />
                                    ) : (
                                        <span className="text-3xl font-mono text-terminal-muted">?</span>
                                    )}
                                </div>
                                <h2 className="text-xl font-mono font-bold text-terminal-text">{selectedChar.name}</h2>
                                <div className="text-xs font-mono text-terminal-muted mt-1">
                                    {selectedChar.job_name} - Lv. {selectedChar.level}
                                </div>
                                {selectedChar.seller && (
                                    <div className="text-[10px] font-mono text-terminal-cyan/70 mt-3 max-w-[200px] truncate" title={selectedChar.seller}>
                                        @{selectedChar.seller.substring(0, 6)}...{selectedChar.seller.substring(selectedChar.seller.length - 4)}
                                    </div>
                                )}
                            </div>

                            {/* Equipment Grid Side */}
                            <div className="flex-1 p-6 flex flex-col items-center justify-center relative bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-opacity-5">
                                <div className="w-full max-w-2xl">
                                    {/* Decorative background blur */}
                                    <div className="absolute inset-0 bg-terminal-cyan/5 mix-blend-overlay pointer-events-none" />

                                    <EquipmentGrid equippedItems={selectedChar.equipped_items || []} />

                                    <div className="mt-8 flex items-center justify-center gap-4">
                                        <button className="flex items-center gap-2 px-4 py-2 bg-terminal-surface border border-terminal-border rounded text-xs font-mono text-terminal-muted hover:text-terminal-text transition-colors">
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                                            </svg>
                                            UNDO
                                        </button>
                                        <button className="flex items-center gap-2 px-6 py-2 bg-terminal-cyan/20 border border-terminal-cyan text-terminal-cyan font-bold rounded text-xs font-mono hover:bg-terminal-cyan/30 transition-colors shadow-[0_0_10px_rgba(var(--terminal-cyan),0.2)]">
                                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                            SAVE BUILD
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {!selectedChar && !loading && results.length === 0 && (
                        <div className="h-96 border border-dashed border-terminal-border/50 rounded-lg flex flex-col items-center justify-center text-terminal-muted space-y-3">
                            <svg className="w-12 h-12 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <span className="text-sm font-mono">Use the search bar to lock onto a target</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
