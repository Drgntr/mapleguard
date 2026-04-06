"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import ItemTooltipContent from "./ItemTooltipContent";

// -- Constants ---------------------------------------------------------------

const POTENTIAL_LABELS: Record<number, { label: string; color: string }> = {
    0: { label: "NORMAL", color: "text-terminal-muted" },
    1: { label: "RARE", color: "text-terminal-cyan" },
    2: { label: "EPIC", color: "text-purple-400" },
    3: { label: "UNIQUE", color: "text-yellow-400" },
    4: { label: "LEGENDARY", color: "text-terminal-green" },
};

const POTENTIAL_BG: Record<number, string> = {
    1: "border-terminal-cyan/30 shadow-[0_0_12px_rgba(0,200,200,0.08)]",
    2: "border-purple-500/30 shadow-[0_0_12px_rgba(168,85,247,0.08)]",
    3: "border-yellow-500/30 shadow-[0_0_12px_rgba(234,179,8,0.08)]",
    4: "border-terminal-green/30 shadow-[0_0_15px_rgba(0,255,128,0.1)]",
};

const SF_BADGE = (n: number) => {
    if (n >= 22) return "text-red-400 font-bold";
    if (n >= 17) return "text-orange-400 font-bold";
    if (n >= 12) return "text-yellow-400";
    return "text-terminal-muted";
};

// -- Types -------------------------------------------------------------------

interface ItemEntry {
    token_id?: string;
    item_id: number;
    name: string;
    starforce: number;
    potential_grade: number;
    bonus_potential_grade: number;
    price?: number;
    price_wei?: string;
    image_url?: string;
    required_level?: number;
}

interface UpgradeVectorsProps {
    sfParams: any;
    potParams: any;
    bpParams: any;
    handleSfChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
    handlePotChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
    handleBpChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
    selectedItem: any;
    setSelectedItem: (item: any) => void;
    itemLevel: number;
    setItemLevel: (lvl: number) => void;
    handleCalculate: () => void;
    loading: boolean;
    result: any;
    showBreakdown: boolean;
    setShowBreakdown: (v: boolean) => void;
    scannedChar?: any;
}

// -- Helpers -----------------------------------------------------------------

function PotBadge({ grade }: { grade: number }) {
    const info = POTENTIAL_LABELS[grade];
    if (!info || grade === 0) return <span className="text-terminal-muted/50 text-[9px]">—</span>;
    return <span className={`${info.color} text-[9px] font-bold uppercase`}>{info.label}</span>;
}

function ItemCard({ item, selected, onClick }: { item: ItemEntry; selected: boolean; onClick: () => void }) {
    const price = item.price_wei ? parseInt(item.price_wei) : (item.price || 0);
    return (
        <div
            onClick={onClick}
            className={`relative flex flex-col items-center cursor-pointer rounded-md border p-1.5 transition-all group
                ${selected
                    ? "border-terminal-accent bg-terminal-accent/10 shadow-[0_0_20px_rgba(var(--terminal-accent),0.2)]"
                    : `bg-terminal-surface/60 hover:bg-terminal-surface border-terminal-border/40 hover:border-terminal-accent/40 ${POTENTIAL_BG[item.potential_grade] || ""}`
                }`}
        >
            <div className="absolute top-1/2 -translate-y-1/2 right-[105%] opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 z-[999] transform">
                <ItemTooltipContent item={item} />
            </div>

            <div className="w-16 h-16 flex items-center justify-center bg-black/30 rounded mb-1.5 overflow-hidden border border-white/5 group-hover:border-terminal-accent/30 transition-all shadow-inner">
                <img
                    src={item.image_url || (item.item_id ? `https://api-static.msu.io/itemimages/icon/${String(item.item_id).padStart(7, '0')}.png` : '')}
                    alt={item.name}
                    className="w-12 h-12 object-contain drop-shadow-md transition-transform group-hover:scale-110"
                    onError={(e) => {
                        const t = e.target as HTMLImageElement;
                        if (t.src && !t.src.includes('0000000')) {
                            const id = String(item.item_id);
                            if (t.src.includes('icon/0')) {
                                t.src = "https://api-static.msu.io/itemimages/icon/0000000.png";
                                t.style.opacity = "0.2";
                            } else {
                                t.src = `https://api-static.msu.io/itemimages/icon/0${id}.png`;
                            }
                        }
                    }}
                />
            </div>

            {item.starforce > 0 && (
                <div className={`absolute top-0.5 left-0.5 text-[8px] font-bold px-0.5 leading-tight ${SF_BADGE(item.starforce)}`}>
                    ★{item.starforce}
                </div>
            )}

            {item.potential_grade > 0 && (
                <div className={`absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full ${item.potential_grade === 4 ? "bg-terminal-green" :
                    item.potential_grade === 3 ? "bg-yellow-400" :
                        item.potential_grade === 2 ? "bg-purple-400" :
                            "bg-terminal-cyan"
                    }`} />
            )}

            <div className="text-[8px] text-terminal-muted group-hover:text-terminal-accent text-center leading-tight truncate w-full max-w-[60px]">
                {item.name}
            </div>

            <div className="text-[8px] text-terminal-green font-mono leading-tight">
                {price > 0 ? `${(price / 1e9).toFixed(1)}B` : "—"}
            </div>
        </div>
    );
}

// -- Main Component ----------------------------------------------------------

export default function UpgradeVectors({
    sfParams, potParams, bpParams,
    handleSfChange, handlePotChange, handleBpChange,
    selectedItem, setSelectedItem,
    itemLevel, setItemLevel,
    handleCalculate, loading, result, showBreakdown, setShowBreakdown,
    scannedChar
}: UpgradeVectorsProps) {

    const [marketItems, setMarketItems] = useState<ItemEntry[]>([]);
    const [marketLoading, setMarketLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [isLastPage, setIsLastPage] = useState(false);

    const [tokenIdInput, setTokenIdInput] = useState("");
    const [idLoading, setIdLoading] = useState(false);
    const [idError, setIdError] = useState("");
    const [suggestions, setSuggestions] = useState<any[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);

    const [sfFilter, setSfFilter] = useState<number | "">("");
    const [potFilter, setPotFilter] = useState<number | "">("");

    // Debounce search
    const debounceTimer = useRef<NodeJS.Timeout | null>(null);

    const performSearch = useCallback(async (q: string) => {
        if (!q || q.length < 2) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }

        try {
            const res = await fetch(`/api/items/lookup?query=${encodeURIComponent(q)}`);
            const data = await res.json();
            if (data.all_results) {
                setSuggestions(data.all_results);
                setShowSuggestions(true);
            } else if (data.item) {
                setSuggestions([data.item]);
                setShowSuggestions(true);
            }
        } catch { }
    }, []);

    const onSearchChange = (val: string) => {
        setTokenIdInput(val);
        setIdError("");
        if (debounceTimer.current) clearTimeout(debounceTimer.current);
        debounceTimer.current = setTimeout(() => performSearch(val), 400);
    };

    const fetchItems = useCallback(async (p: number) => {
        setMarketLoading(true);
        try {
            const res = await fetch(`/api/items?page=${p}&page_size=24`);
            const data = await res.json();
            setMarketItems(prev => p === 1 ? data.items : [...prev, ...data.items]);
            setIsLastPage(data.is_last_page);
        } catch { }
        setMarketLoading(false);
    }, []);

    useEffect(() => { fetchItems(1); }, [fetchItems]);
    useEffect(() => { if (page > 1) fetchItems(page); }, [page, fetchItems]);

    const handleLookup = async (e: React.FormEvent) => {
        e.preventDefault();
        const q = tokenIdInput.trim();
        if (!q) return;
        setIdLoading(true);
        setIdError("");
        setSuggestions([]);
        setShowSuggestions(false);
        try {
            const res = await fetch(`/api/items/lookup?query=${encodeURIComponent(q)}`);
            const data = await res.json();
            if (data.error) {
                setIdError(data.error);
            } else if (data.item) {
                if (data.all_results && data.all_results.length > 1) {
                    setSuggestions(data.all_results);
                    setShowSuggestions(true);
                } else {
                    applyLookupResult(data.item);
                }
            }
        } catch {
            setIdError("Network error");
        }
        setIdLoading(false);
    };

    const applyLookupResult = (item: any) => {
        setSelectedItem(item);
        setItemLevel(item.required_level || 200);
        setTokenIdInput("");
        setSuggestions([]);
        setShowSuggestions(false);
    };

    const filtered = marketItems.filter(item => {
        if (sfFilter !== "" && item.starforce < Number(sfFilter)) return false;
        if (potFilter !== "" && item.potential_grade < Number(potFilter)) return false;
        return true;
    });

    return (
        <div className="bg-terminal-panel border border-terminal-accent/30 rounded-lg shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-t-2 border-t-terminal-accent overflow-hidden h-full flex flex-col">
            <div className="flex items-center gap-3 px-5 py-4 border-b border-terminal-border/50 bg-terminal-panel/20">
                <span className="w-2 h-2 bg-terminal-accent animate-ping rounded-full flex-shrink-0" />
                <h2 className="text-xs font-bold text-terminal-text uppercase tracking-widest">Enhancement Vectors</h2>
            </div>

            <div className="p-5 flex-1 flex flex-col gap-5">
                {/* Search Item Section */}
                <div className="relative">
                    <div className="text-[10px] font-bold text-terminal-accent uppercase tracking-widest mb-1.5 flex justify-between">
                        <span>Dynamic Search</span>
                        {scannedChar && <span className="text-[9px] text-terminal-green animate-pulse">Char Detected: {scannedChar.nickname}</span>}
                    </div>
                    <form onSubmit={handleLookup} className="flex gap-2">
                        <input
                            type="text"
                            value={tokenIdInput}
                            onChange={e => onSearchChange(e.target.value)}
                            placeholder="NAME, NFT ID, or ASSET KEY..."
                            className="flex-1 bg-terminal-surface border border-terminal-border text-terminal-text text-[11px] px-3 py-2.5 rounded outline-none focus:border-terminal-accent font-mono placeholder:text-terminal-muted/40 transition-all focus:bg-terminal-surface/40"
                        />
                        <button type="submit" disabled={idLoading}
                            className="bg-terminal-panel border border-terminal-accent/40 text-terminal-accent hover:bg-terminal-accent hover:text-black font-bold text-[11px] px-4 py-1.5 rounded transition-all disabled:opacity-50 whitespace-nowrap uppercase tracking-widest"
                        >
                            {idLoading ? "..." : "FIND"}
                        </button>
                    </form>
                    {idError && <div className="text-red-400 text-[10px] mt-1">{idError}</div>}

                    {showSuggestions && suggestions.length > 0 && (
                        <div className="absolute left-0 right-0 z-[100] mt-1 bg-terminal-panel border border-terminal-accent/40 rounded shadow-2xl max-h-64 overflow-y-auto backdrop-blur-md">
                            <div className="px-3 py-2 text-[10px] text-terminal-muted border-b border-terminal-border bg-black/40 uppercase tracking-widest flex justify-between items-center">
                                <span>Found {suggestions.length} Matches</span>
                                <button onClick={() => setShowSuggestions(false)} className="hover:text-terminal-red">ESC</button>
                            </div>
                            {suggestions.map((s: any, i: number) => (
                                <div key={i} onClick={() => applyLookupResult(s)}
                                    className="flex items-center gap-4 px-3 py-2.5 hover:bg-terminal-accent/20 cursor-pointer transition-all border-b border-terminal-border/20 last:border-0 group"
                                >
                                    <div className="w-10 h-10 bg-black/40 rounded flex items-center justify-center p-1 border border-terminal-border group-hover:border-terminal-accent/40">
                                        <img src={s.image_url || `https://api-static.msu.io/itemimages/icon/${s.item_id}.png`} alt="" className="w-full h-full object-contain"
                                            onError={(e) => {
                                                const t = e.target as HTMLImageElement;
                                                if (t.src && !t.src.includes('0000000')) {
                                                    const id = String(s.item_id);
                                                    if (t.src.includes('icon/0')) {
                                                        t.src = "https://api-static.msu.io/itemimages/icon/0000000.png";
                                                        t.style.opacity = "0.2";
                                                    } else {
                                                        t.src = `https://api-static.msu.io/itemimages/icon/0${id}.png`;
                                                    }
                                                }
                                            }}
                                        />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-[12px] font-bold text-terminal-text group-hover:text-terminal-accent transition-colors">{s.name}</div>
                                        <div className="text-[10px] text-terminal-muted flex gap-2 items-center">
                                            {s.required_level && <span className="bg-terminal-surface px-1.5 rounded">LV {s.required_level}</span>}
                                            {s.starforce > 0 && <span className="text-yellow-400">★{s.starforce}</span>}
                                            {s.potential_grade > 0 && <span className={POTENTIAL_LABELS[s.potential_grade]?.color}>POT</span>}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Selected Item Detail */}
                {selectedItem ? (
                    <div className={`p-4 rounded-lg border ${POTENTIAL_BG[selectedItem.potential_grade] || "border-terminal-accent/20"} bg-terminal-accent/5 backdrop-blur-sm relative overflow-hidden group`}>
                        <div className="relative z-10 flex gap-6">
                            <div className="w-24 h-24 bg-black/50 border border-terminal-accent/30 rounded-xl flex items-center justify-center p-3 shadow-2xl group-hover:scale-110 transition-transform duration-500">
                                <img src={selectedItem.image_url || (selectedItem.item_id ? `https://api-static.msu.io/itemimages/icon/${String(selectedItem.item_id).padStart(7, '0')}.png` : '')}
                                    alt="" className="w-20 h-20 object-contain filter drop-shadow-[0_5px_15px_rgba(0,0,0,0.8)]"
                                    onError={(e) => {
                                        const t = e.target as HTMLImageElement;
                                        if (t.src && !t.src.includes('0000000')) {
                                            const id = String(selectedItem.item_id);
                                            if (t.src.includes('icon/0')) {
                                                t.src = "https://api-static.msu.io/itemimages/icon/0000000.png";
                                                t.style.opacity = "0.2";
                                            } else {
                                                t.src = `https://api-static.msu.io/itemimages/icon/0${id}.png`;
                                            }
                                        }
                                    }}
                                />
                            </div>
                            <div className="flex-1 pt-1">
                                <div className="text-lg font-black text-white mb-2 uppercase tracking-tighter leading-none">{selectedItem.name}</div>
                                <div className="flex flex-wrap gap-2.5 mb-4">
                                    {selectedItem.starforce > 0 && <div className={`text-[11px] font-black px-2 py-0.5 rounded ${SF_BADGE(selectedItem.starforce)} shadow-[0_0_10px_rgba(var(--terminal-accent),0.3)]`}>★ {selectedItem.starforce}</div>}
                                    <PotBadge grade={selectedItem.potential_grade} />
                                    {selectedItem.price_wei && <div className="text-[11px] text-terminal-green font-black bg-terminal-green/10 border border-terminal-green/20 px-2 py-0.5 rounded tracking-tighter">{(parseInt(selectedItem.price_wei) / 1e9).toLocaleString()}B NESO</div>}
                                </div>
                                <div className="flex items-center gap-4 bg-black/30 p-2 rounded border border-white/5">
                                    <span className="text-[11px] font-black text-terminal-muted uppercase tracking-widest">Base Level:</span>
                                    <input type="number" value={itemLevel} onChange={e => setItemLevel(Number(e.target.value))}
                                        className="w-20 bg-black/60 border border-white/10 text-terminal-accent text-sm font-black px-2 py-1 rounded outline-none focus:border-terminal-accent transition-all" />
                                </div>
                            </div>
                            <button onClick={() => setSelectedItem(null)} className="absolute top-2 right-2 text-terminal-muted/40 hover:text-terminal-red text-lg">✕</button>
                        </div>
                        <div className="absolute top-0 right-0 w-24 h-24 bg-terminal-accent/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                ) : (
                    <div className="border border-dashed border-terminal-border/40 rounded-lg p-8 flex flex-col items-center justify-center gap-3 opacity-30">
                        <svg className="w-10 h-10 text-terminal-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                        <span className="text-[10px] uppercase tracking-widest text-center">No Target Selected<br />Fetch from Market or Grid</span>
                    </div>
                )}

                {/* Marketplace Integration Grid */}
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <div className="text-[10px] font-bold text-terminal-muted uppercase tracking-[.2em]">Market Browser</div>
                        <div className="flex gap-2">
                            <select value={sfFilter} onChange={e => setSfFilter(e.target.value === "" ? "" : Number(e.target.value))} className="bg-terminal-surface border border-terminal-border text-terminal-muted text-[8px] px-1.5 py-1 rounded outline-none">
                                <option value="">★ ALL</option>
                                {[17, 20, 22].map(n => <option key={n} value={n}>≥★{n}</option>)}
                            </select>
                            <select value={potFilter} onChange={e => setPotFilter(e.target.value === "" ? "" : Number(e.target.value))} className="bg-terminal-surface border border-terminal-border text-terminal-muted text-[8px] px-1.5 py-1 rounded outline-none">
                                <option value="">💎 ALL</option>
                                <option value="3">UNIQUE</option>
                                <option value="4">LEGD</option>
                            </select>
                        </div>
                    </div>
                    <div className="grid grid-cols-4 gap-2 max-h-[220px] overflow-y-auto scrollbar-terminal pr-1">
                        {filtered.map(item => (
                            <ItemCard key={item.token_id} item={item} selected={selectedItem?.token_id === item.token_id}
                                onClick={() => { setSelectedItem(item); setItemLevel(item.required_level || 200); }}
                            />
                        ))}
                        {marketLoading && Array.from({ length: 4 }).map((_, i) => <div key={i} className="aspect-square bg-terminal-surface/20 animate-pulse rounded" />)}
                    </div>
                    {!isLastPage && !marketLoading && (
                        <button onClick={() => setPage(p => p + 1)} className="w-full py-1.5 text-[9px] text-terminal-muted border border-terminal-border/30 rounded hover:text-terminal-accent transition-all uppercase tracking-widest">More Data...</button>
                    )}
                </div>

                {/* Simulation Parameters */}
                <div className="space-y-4 pt-4 border-t border-terminal-border">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[9px] text-terminal-muted font-bold uppercase">Starforce Goal</label>
                            <input name="target_sf" type="number" value={sfParams.target_sf} onChange={handleSfChange}
                                className="w-full bg-terminal-surface border border-terminal-border text-center text-terminal-accent text-lg py-2 rounded focus:border-terminal-accent outline-none" />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[9px] text-terminal-muted font-bold uppercase">Target Tier</label>
                            <select name="target_potential" value={potParams.target_potential} onChange={handlePotChange}
                                className="w-full h-[46px] bg-terminal-surface border border-terminal-border text-terminal-text text-[11px] px-2 rounded focus:border-terminal-accent outline-none">
                                {["Normal", "Rare", "Epic", "Unique", "Legendary"].map(o => <option key={o}>{o}</option>)}
                            </select>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[9px] text-terminal-muted font-bold uppercase">Potential Stat Focus</label>
                        <select name="primary_stat_goal" value={potParams.primary_stat_goal} onChange={handlePotChange}
                            className="w-full bg-terminal-surface border border-terminal-border text-terminal-text text-xs py-2 px-3 rounded">
                            <option value="">Any Result</option>
                            <option value="2L_MAIN_STAT">2L Main Stat</option>
                            <option value="3L_MAIN_STAT">3L Main Stat</option>
                            <option value="2L_BOSS">2L Boss Damage</option>
                        </select>
                    </div>

                    <button onClick={handleCalculate} disabled={loading || !selectedItem}
                        className={`w-full py-4 font-black transition-all shadow-xl tracking-[.4em] text-xs uppercase
                            ${loading || !selectedItem ? "bg-terminal-muted/20 text-terminal-muted cursor-not-allowed" : "bg-terminal-accent text-black hover:scale-[1.02] hover:shadow-[0_0_30px_rgba(var(--terminal-accent),0.3)]"}
                        `}
                    >
                        {loading ? "Simulating Quantum Probabilities..." : "Execute Simulation"}
                    </button>
                </div>

                {/* Result Block */}
                {result && (
                    <div className="bg-black/60 p-4 rounded border border-terminal-accent/30 animate-in fade-in slide-in-from-bottom-2">
                        <div className="flex justify-between items-center mb-4">
                            <div className="text-[12px] font-bold text-terminal-text uppercase">Combat Rating Upgrade</div>
                            {result.sf_cp_upgrade ? (
                                <div className="text-xl font-bold text-terminal-green">+{result.sf_cp_upgrade.cp_gain.toLocaleString()}</div>
                            ) : (
                                <div className="text-xl font-bold text-terminal-green">+{result.cp_gain_pct}% CP</div>
                            )}
                        </div>
                        <div className="grid grid-cols-2 gap-3 mb-4">
                            <div className="p-2 border border-terminal-border rounded">
                                <span className="block text-[8px] text-terminal-muted uppercase">Avg. NESO Spent</span>
                                <span className="text-[13px] font-bold">{result.total_expected_cost?.toLocaleString()}B+</span>
                            </div>
                            <div className="p-2 border border-terminal-border rounded">
                                <span className="block text-[8px] text-terminal-muted uppercase">Median Tries</span>
                                <span className="text-[13px] font-bold">{result.median_tries || 12}</span>
                            </div>
                        </div>
                        <button onClick={() => setShowBreakdown(!showBreakdown)}
                            className="w-full text-[9px] text-terminal-muted hover:text-terminal-accent underline uppercase tracking-widest text-center"
                        >
                            {showBreakdown ? "Hide Distribution Data" : "Detailed Step Breakdown View"}
                        </button>

                        {showBreakdown && result.sf_cp_upgrade?.per_star && (
                            <div className="mt-4 border-t border-terminal-border pt-4">
                                <div className="flex justify-between items-center text-[8px] text-terminal-muted uppercase tracking-widest mb-3 pb-2 border-b border-white/5">
                                    <div className="w-8">Lvl</div>
                                    <div className="flex-1 text-center">Gain Per Star</div>
                                    <div className="w-16 text-right">CP Gain</div>
                                </div>
                                <div className="space-y-1 max-h-[250px] overflow-y-auto scrollbar-terminal pr-2">
                                    {result.sf_cp_upgrade.per_star.map((s: any) => (
                                        <div key={s.star} className="flex justify-between items-center text-[10px] p-2 bg-black/40 border border-white/5 rounded font-mono group hover:border-terminal-accent/30 hover:bg-terminal-accent/5 transition-all">
                                            <div className="w-8 font-black text-white group-hover:text-terminal-accent">★{s.star}</div>
                                            <div className="flex-1 text-center text-white/50">
                                                +{s.stat_gain} STAT
                                                {s.att_gain > 0 && <span className="text-terminal-cyan ml-2">+{s.att_gain} ATT</span>}
                                            </div>
                                            <div className="w-16 text-right font-black text-terminal-green whitespace-nowrap">
                                                +{s.cp_gain_from_current >= 1000 ? (s.cp_gain_from_current / 1000).toFixed(1) + 'k' : Math.round(s.cp_gain_from_current)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="mt-3 pt-3 border-t border-white/5 flex justify-between items-center text-[11px] font-black font-mono">
                                    <div className="text-terminal-muted uppercase tracking-widest">TOTAL</div>
                                    <div className="text-terminal-accent">+{result.sf_cp_upgrade.stat_delta.primary_stat} STAT {result.sf_cp_upgrade.stat_delta.att > 0 && `/ +${result.sf_cp_upgrade.stat_delta.att} ATT`}</div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
