"use client";

import { useState } from "react";
import { useItems } from "@/hooks/useMarketData";
import EquipmentGrid from "@/components/EquipmentGrid";
import HyperStatsGrid from "@/components/HyperStatsGrid";
import UpgradeVectors from "@/components/UpgradeVectors";
import ItemTooltipContent from "@/components/ItemTooltipContent";

const POTENTIAL_LABELS: Record<number, [string, string]> = {
    0: ["NONE", "text-terminal-muted"],
    1: ["RARE", "badge-cyan"],
    2: ["EPIC", "badge-purple"],
    3: ["UNIQUE", "badge-yellow"],
    4: ["LEGENDARY", "badge-green"],
    5: ["SPECIAL", "badge-red"],
    6: ["MYTHIC", "badge-red"],
};

export default function CalculatorPage() {
    const [page, setPage] = useState(1);
    const [sorting, setSorting] = useState("ExploreSorting_RECENTLY_LISTED");
    const { data: marketData, isLoading: marketLoading } = useItems(page, 12, sorting);
    const marketItems = marketData?.items || [];

    const [charQuery, setCharQuery] = useState("");
    const [charSearching, setCharSearching] = useState(false);
    const [charResults, setCharResults] = useState<any[]>([]);
    const [selectedChar, setSelectedChar] = useState<any>(null);

    const [baseCp, setBaseCp] = useState<number | null>(null);
    const [selectedItem, setSelectedItem] = useState<any>(null);
    const [legionBlocks, setLegionBlocks] = useState(0);
    const [collectionScore, setCollectionScore] = useState(0);
    const [legionPreview, setLegionPreview] = useState<any>(null);
    const [collectionPreview, setCollectionPreview] = useState<any>(null);
    const [oldStats, setOldStats] = useState({ main_stat: 1000, sub_stat: 500, attack: 500, attack_percent: 10, damage_percent: 20, boss_damage_percent: 10, final_damage_percent: 0, crit_damage_percent: 30 });
    const [newStats, setNewStats] = useState({ main_stat: 1050, sub_stat: 520, attack: 550, attack_percent: 15, damage_percent: 20, boss_damage_percent: 10, final_damage_percent: 0, crit_damage_percent: 30 });

    const [catalogQuery, setCatalogQuery] = useState("");
    const [catalogSearching, setCatalogSearching] = useState(false);
    const [catalogResults, setCatalogResults] = useState<any[]>([]);

    const [sfParams, setSfParams] = useState({ current_sf: 10, target_sf: 15, sf_cost_per_try: 0, sf_replace_cost: 0 });
    const [potParams, setPotParams] = useState({ current_potential: "Epic", target_potential: "Legendary", cube_type: "Red", cube_cost: 0, primary_stat_goal: "" });
    const [bpParams, setBpParams] = useState({ current_bp: "Normal", target_bp: "Unique", bp_cube_type: "Additional", bp_cube_cost: 0, bonus_stat_goal: "" });

    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState("Equipment");
    const [showBreakdown, setShowBreakdown] = useState(false);
    const [itemLevel, setItemLevel] = useState(200);

    const handleCharSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!charQuery) return;
        setCharSearching(true);
        setCharResults([]);
        setSelectedChar(null);
        try {
            const res = await fetch(`/api/characters/search?query=${encodeURIComponent(charQuery)}`);
            const data = await res.json();
            if (data.results?.length === 1) {
                handleSelectChar(data.results[0].token_id);
            } else {
                setCharResults(data.results || []);
            }
        } catch (e) { console.error(e); }
        setCharSearching(false);
    };

    const handleSelectChar = async (tokenId: string) => {
        setCharSearching(true);
        setCharResults([]);
        try {
            const res = await fetch(`/api/characters/${encodeURIComponent(tokenId)}/detail`);
            const data = await res.json();
            if (data.character) {
                setSelectedChar(data.character);
                const char = data.character;

                // Extract real CP from character
                const realCp = char.char_cp || char.ap_stats?.combat_power?.total || 0;
                if (realCp > 0) setBaseCp(realCp);
                else setBaseCp(0);

                if (char.ap_stats) {
                    const s = char.ap_stats;
                    const mainVal = Math.round(Math.max(s.str_stat?.total || 0, s.int_stat?.total || 0, s.dex?.total || 0, s.luk?.total || 0));
                    const subMap: Record<string, string> = {
                        Archer: 'dex', Thief: 'luk', Warrior: 'str', Magician: 'int', Pirate: 'luk',
                    };
                    const subKey = subMap[char.class_name] || 'dex';
                    const subVal = Math.round(s[`${subKey}_stat`]?.total || s[subKey]?.total || 500);
                    setOldStats({
                        main_stat: mainVal,
                        sub_stat: subVal,
                        attack: Math.round(s.pad?.total || s.physicalAttack?.total || 500),
                        attack_percent: Math.round(s.attack?.total || s.attack_percent || 10),
                        damage_percent: Math.round(s.damage?.total || 20),
                        boss_damage_percent: Math.round(s.boss_monster_damage?.total || 10),
                        final_damage_percent: Math.round(s.final_damage?.total || 0),
                        crit_damage_percent: Math.round(s.critical_damage?.total || 30),
                    });
                    setNewStats(prev => ({
                        ...prev,
                        main_stat: mainVal,
                        sub_stat: subVal,
                        attack: Math.round(s.pad?.total || s.physicalAttack?.total || 500),
                    }));

                    // Auto-set legion/collection defaults from character level
                    if (char.level) {
                        setLegionBlocks(char.level >= 250 ? 7 : char.level >= 200 ? 4 : char.level >= 140 ? 3 : char.level >= 100 ? 2 : 0);
                        setCollectionScore(char.level >= 200 ? 250 : char.level >= 140 ? 60 : 0);
                    }
                }
            }
        } catch (e) { console.error(e); }
        setCharSearching(false);
    };

    const handleCatalogSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        setCatalogSearching(true);
        try {
            const res = await fetch(`/api/items/catalog?query=${encodeURIComponent(catalogQuery)}`);
            const data = await res.json();
            setCatalogResults(data.items || []);
        } catch (e) { console.error(e); }
        setCatalogSearching(false);
    };

    const handleSelectFromCatalog = (item: any) => {
        setSelectedItem(item);
        setSfParams(prev => ({ ...prev, current_sf: 0, target_sf: 17 }));
        setPotParams(prev => ({ ...prev, current_potential: "Normal" }));
        setItemLevel(item.level || 200);
        setCatalogResults([]);
        setCatalogQuery("");
    };

    const handleSelectItem = (item: any) => {
        setSelectedItem(item);
        const tier = POTENTIAL_LABELS[item.potential_grade]?.[0] || "Normal";
        setSfParams(prev => ({ ...prev, current_sf: item.starforce || 0, target_sf: Math.max(item.starforce || 0, 15) }));
        setPotParams(prev => ({ ...prev, current_potential: tier }));
        setItemLevel(item.required_level || 200);
    };

    const handleCalculate = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/calculator/estimate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    base_cp: baseCp || 0,
                    char_stats: oldStats,
                    item_type: selectedItem?.category_label?.toLowerCase().includes("weapon") ? "weapon" : "armor",
                    old_stats: oldStats,
                    new_stats: newStats,
                    current_sf: sfParams.current_sf,
                    target_sf: sfParams.target_sf,
                    item_id: selectedItem?.item_id,
                    item_level: itemLevel,
                    current_potential: potParams.current_potential,
                    target_potential: potParams.target_potential,
                    cube_type: potParams.cube_type,
                    cube_cost: potParams.cube_cost || 15000000,
                    primary_stat_goal: potParams.primary_stat_goal,
                    legion_blocks: legionBlocks,
                    collection_score: collectionScore,
                }),
            });
            const data = await res.json();
            setResult(data);
            if (legionBlocks > 0) setLegionPreview(data.legion_bonus || null);
            if (collectionScore > 0) setCollectionPreview(data.collection_bonus || null);
        } catch (e) { console.error(e); }
        setLoading(false);
    };

    const handleSfChange = (e: any) => setSfParams({ ...sfParams, [e.target.name]: parseInt(e.target.value) || 0 });
    const handlePotChange = (e: any) => setPotParams({ ...potParams, [e.target.name]: e.target.value });
    const handleBpChange = (e: any) => setBpParams({ ...bpParams, [e.target.name]: e.target.value });

    return (
        <div className="flex flex-col h-full overflow-hidden bg-[#07080a] text-terminal-text font-mono selection:bg-terminal-accent/30">
            {/* Ultra-Wide Header */}
            <div className="flex-none p-10 border-b border-white/5 bg-[#090b0e] relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-terminal-accent/10 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between max-w-[1800px] mx-auto relative z-10">
                    <div>
                        <h1 className="text-5xl font-black text-terminal-accent tracking-[.5em] uppercase flex items-center gap-8">
                            <span className="w-4 h-14 bg-terminal-accent inline-block shadow-[0_0_40px_rgba(var(--terminal-accent),0.6)]" />
                            MAPLEGUARD <span className="text-white/10 font-thin">/</span> SCANNER
                        </h1>
                        <p className="text-[12px] text-white/40 mt-3 uppercase tracking-[1em] flex items-center gap-4">
                            <span className="w-3 h-3 rounded-full bg-terminal-green animate-pulse shadow-[0_0_12px_rgba(var(--terminal-green),1)]" />
                            Integrated Gear Analysis Engine V4.0.2
                        </p>
                    </div>
                    <div className="text-right">
                        <div className="text-[10px] text-white/20 uppercase tracking-widest font-black">Local Node</div>
                        <div className="text-sm font-black text-terminal-accent">PROXIMA-7 // ACTIVE</div>
                    </div>
                </div>
            </div>

            {/* Main Scrollable Workspace */}
            <div className="flex-1 overflow-y-auto p-12 scrollbar-terminal bg-[radial-gradient(circle_at_bottom_left,_rgba(0,180,180,0.05),_transparent_50%)]">
                <div className="max-w-[1800px] mx-auto space-y-12">

                    {/* Top Section: Sidebar + Core Analysis */}
                    <div className="grid grid-cols-1 xl:grid-cols-[400px_1fr_420px] gap-12 items-stretch">

                        {/* LEFT: Target Protocols + System Differential */}
                        <div className="space-y-8 h-full flex flex-col">
                            <div className="bg-[#111317] border border-white/10 rounded-2xl p-8 shadow-3xl backdrop-blur-2xl ring-1 ring-white/5 overflow-hidden relative group">
                                <div className="absolute top-0 left-0 w-1 h-full bg-terminal-accent opacity-30" />
                                <h2 className="text-xs font-black text-terminal-accent uppercase mb-8 tracking-[.5em] flex items-center gap-4">
                                    <span className="w-2 h-5 bg-terminal-accent/20" />
                                    PROTOCOL: SCAN
                                </h2>
                                <form onSubmit={handleCharSearch} className="flex gap-3 mb-10">
                                    <input
                                        type="text"
                                        placeholder="NICKNAME / TOKEN..."
                                        value={charQuery}
                                        onChange={(e) => setCharQuery(e.target.value)}
                                        disabled={charSearching}
                                        className={`flex-1 bg-black/60 border text-terminal-text px-5 py-4 text-sm outline-none transition-all rounded-lg font-mono placeholder:text-white/10 ${
                                            charSearching
                                                ? "border-terminal-accent/50 opacity-60 cursor-not-allowed"
                                                : "border-white/10 focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent/20"
                                        }`}
                                    />
                                    <button type="submit" disabled={charSearching} className={`flex items-center justify-center gap-2 text-black px-6 py-4 text-xs font-black rounded-lg transition-all ${
                                        charSearching
                                            ? "bg-terminal-accent animate-pulse shadow-[0_0_40px_rgba(var(--terminal-accent),0.6)] scale-105"
                                            : "bg-terminal-accent hover:scale-105 active:scale-95 disabled:opacity-50 shadow-[0_0_30px_rgba(var(--terminal-accent),0.3)]"
                                    }`}>
                                        {charSearching && (
                                            <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                        )}
                                        {charSearching ? "SCANNING..." : "SCAN"}
                                    </button>
                                </form>

                                {charSearching && !selectedChar && charResults.length === 0 && (
                                    <div className="py-12 flex flex-col items-center justify-center gap-4 animate-in fade-in duration-300">
                                        <div className="relative w-16 h-16">
                                            <div className="absolute inset-0 border-2 border-terminal-accent/20 rounded-full" />
                                            <div className="absolute inset-0 border-2 border-transparent border-t-terminal-accent rounded-full animate-spin" />
                                            <div className="absolute inset-2 border-2 border-transparent border-b-terminal-accent/60 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
                                        </div>
                                        <div className="text-sm font-black text-terminal-accent tracking-[0.3em] uppercase animate-pulse">
                                            SCANNING TARGET...
                                        </div>
                                        <div className="w-48 bg-black/40 rounded-full h-1.5 overflow-hidden">
                                            <div className="h-full bg-gradient-to-r from-terminal-accent/40 via-terminal-accent to-terminal-accent/40 rounded-full" style={{ width: '70%', animation: 'loading 1.5s ease-in-out infinite' }} />
                                        </div>
                                    </div>
                                )}

                                {selectedChar ? (
                                    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                        <div className="relative w-56 h-56 mx-auto">
                                            <div className="absolute inset-0 bg-terminal-accent/15 rounded-full blur-[60px] animate-pulse" />
                                            <div className="relative w-full h-full rounded-2xl border-4 border-white/5 bg-[#0d0f12] shadow-[0_25px_60px_rgba(0,0,0,0.9)] flex items-center justify-center p-10 overflow-hidden transform transition-all hover:border-terminal-accent/40 group">
                                                <img src={selectedChar.image_url} alt="" className="w-full h-full object-contain filter contrast-125 brightness-110 drop-shadow-[0_0_20px_rgba(0,0,0,0.8)] z-10 transition-transform duration-700 group-hover:scale-110" />
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-60 pointer-events-none" />
                                            </div>
                                        </div>
                                        <div className="text-center space-y-3">
                                            <h3 className="text-2xl font-black text-white tracking-[0.1em] uppercase">{selectedChar.nickname}</h3>
                                            <div className="inline-flex items-center gap-3 bg-terminal-accent/5 border border-terminal-accent/20 rounded-full px-6 py-2">
                                                <div className="w-2 h-2 rounded-full bg-terminal-accent shadow-[0_0_8px_rgba(var(--terminal-accent),1)]" />
                                                <span className="text-[12px] font-black text-terminal-accent uppercase tracking-[0.3em]">{selectedChar.job_name || "Combat Unit"}</span>
                                            </div>
                                        </div>
                                    </div>
                                ) : charResults.length > 0 ? (
                                    <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 scrollbar-terminal py-2">
                                        {charResults.map((c: any) => (
                                            <div key={c.token_id} onClick={() => handleSelectChar(c.token_id)}
                                                className="flex items-center gap-4 p-4 bg-black/40 border border-white/5 hover:border-terminal-accent/40 rounded-xl cursor-pointer transition-all group">
                                                <div className="w-12 h-12 rounded-lg bg-[#0d0f12] border border-white/5 flex items-center justify-center overflow-hidden">
                                                    <img src={c.image_url} className="w-full h-full object-contain group-hover:scale-110 transition-transform" />
                                                </div>
                                                <div className="flex-1">
                                                    <div className="text-xs font-black text-white group-hover:text-terminal-accent transition-colors">{c.nickname || c.name}</div>
                                                    <div className="text-[9px] text-white/20 uppercase tracking-widest">{c.job_name || "Unknown Job"}</div>
                                                </div>
                                                <div className="text-[10px] text-terminal-accent opacity-0 group-hover:opacity-100 font-black">SCAN »</div>
                                            </div>
                                        ))}
                                    </div>
                                ) : !charSearching ? (
                                    <div className="py-24 flex flex-col items-center justify-center opacity-10 text-white gap-6">
                                        <div className="w-20 h-20 rounded-full border border-dashed border-white/40 flex items-center justify-center">
                                            <div className="w-10 h-10 bg-white/20 rounded-full animate-ping" />
                                        </div>
                                        <span className="text-[12px] font-black tracking-[0.5em] uppercase text-center">Awaiting Target Acquisition</span>
                                    </div>
                                ) : null}
                            </div>

                            {/* System Differential Analysis (Moved here from center) */}
                            <div className="flex-1 bg-[#111317] border border-white/5 rounded-2xl p-8 shadow-3xl backdrop-blur-2xl ring-1 ring-white/5 overflow-y-auto scrollbar-terminal min-h-[400px]">
                                <div className="flex items-center justify-between mb-8 border-b border-white/5 pb-6">
                                    <h2 className="text-[12px] font-black text-terminal-accent tracking-[.3em] uppercase flex items-center gap-4">
                                        <span className="w-2 h-5 bg-terminal-accent/30 animate-pulse" />
                                        DIFFERENTIAL
                                    </h2>
                                    <div className="flex flex-col gap-1 items-end text-[9px] font-black tracking-tighter">
                                        <span className="text-white/20 uppercase tracking-widest">PRE: PRE-SIM</span>
                                        <span className="text-terminal-accent uppercase tracking-widest">PROJ: PROJECTED</span>
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    {Object.entries(oldStats).map(([key, oldVal]) => {
                                        const newVal = (newStats as any)[key];
                                        const diff = newVal - oldVal;
                                        const pct = oldVal !== 0 ? ((diff / oldVal) * 100).toFixed(1) : "0.0";
                                        return (
                                            <div key={key} className="bg-black/40 border border-white/5 p-5 rounded-xl hover:border-terminal-accent/30 transition-all group relative overflow-hidden">
                                                <div className="text-[9px] text-white/30 font-black uppercase tracking-[.2em] mb-3">{key.replace(/_/g, " ")}</div>
                                                <div className="flex items-end justify-between">
                                                    <div className="space-y-0.5">
                                                        <div className="text-lg font-black text-white font-mono leading-none">{newVal.toLocaleString()}</div>
                                                        <div className="text-[9px] text-white/10 font-mono">PRE: {oldVal.toLocaleString()}</div>
                                                    </div>
                                                    <div className={`text-[11px] font-black font-mono px-2 py-0.5 rounded ${diff >= 0 ? "text-terminal-green bg-terminal-green/5 border border-terminal-green/10" : "text-terminal-red bg-terminal-red/5 border border-terminal-red/10"}`}>
                                                        {diff >= 0 ? "+" : ""}{pct}%
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        {/* CENTER: Loadout Grid */}
                        <div className="space-y-12 h-full flex flex-col">
                            <div className="bg-[#111317] border border-white/5 rounded-3xl overflow-visible shadow-4xl ring-1 ring-white/5 relative flex-1 flex flex-col">
                                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-terminal-accent/5 rounded-full blur-[150px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                                <div className="flex border-b border-white/5 bg-black/40 rounded-t-3xl">
                                    {["Equipment", "Hyper Stats", "Legion & Collection"].map(tab => (
                                        <button key={tab} onClick={() => setActiveTab(tab)}
                                            className={`flex-1 py-7 text-[13px] font-black tracking-[0.4em] uppercase transition-all relative
                                                ${activeTab === tab ? "text-terminal-accent bg-terminal-accent/5" : "text-white/20 hover:text-white/50"}
                                            `}>
                                            {tab}
                                            {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-1 bg-terminal-accent shadow-[0_0_30px_rgba(var(--terminal-accent),1)]" />}
                                        </button>
                                    ))}
                                </div>
                                <div className="pt-8 pb-14 px-14 flex-1 w-full flex items-start justify-center gap-14 overflow-visible relative z-10">
                                    {activeTab === "Equipment" ? (
                                        <>
                                            {/* LEFT: Gear Grid */}
                                            <div className="flex-none">
                                                <EquipmentGrid
                                                    equippedItems={selectedChar?.equipped_items || []}
                                                    onSelect={handleSelectItem}
                                                    selectedId={selectedItem?.token_id}
                                                />
                                            </div>

                                            {/* RIGHT: Status Monitor */}
                                            {selectedChar && (
                                                <div className="w-[300px] flex flex-col gap-5 animate-in fade-in slide-in-from-right-8 duration-700">

                                                    {/* CP Console */}
                                                    <div className="bg-black/80 border-2 border-terminal-accent/20 rounded-2xl p-6 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                                                        <div className="absolute top-0 right-0 w-32 h-32 bg-terminal-accent/5 rounded-full blur-3xl group-hover:bg-terminal-accent/15 transition-colors" />
                                                        <div className="text-[9px] font-black text-terminal-accent uppercase tracking-[0.4em] mb-3">AGGREGATE COMBAT RATING</div>
                                                        <div className="text-4xl font-black text-white font-mono tracking-tighter drop-shadow-[0_0_20px_rgba(var(--terminal-accent),0.4)]">
                                                            {(selectedChar.char_cp || selectedChar.ap_stats?.combat_power?.total || 0).toLocaleString()}
                                                        </div>
                                                        <div className="mt-5 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                                            <div className="h-full bg-terminal-accent w-5/6 shadow-[0_0_15px_rgba(var(--terminal-accent),0.6)]" />
                                                        </div>
                                                    </div>

                                                    {/* Primary Stats Cluster */}
                                                    <div className="grid grid-cols-2 gap-2">
                                                        {[
                                                            { key: 'str', label: 'STR' },
                                                            { key: 'dex', label: 'DEX' },
                                                            { key: 'int', label: 'INT' },
                                                            { key: 'luk', label: 'LUK' },
                                                        ].map(s => {
                                                            const val = selectedChar.ap_stats?.[`${s.key}_stat`]?.total || selectedChar.ap_stats?.[s.key]?.total || 0;
                                                            return (
                                                                <div key={s.label} className="bg-white/[0.02] border border-white/5 rounded-xl px-4 py-3 flex flex-col group hover:border-terminal-accent/20 transition-all hover:bg-white/[0.04]">
                                                                    <span className="text-[8px] font-black text-white/20 uppercase tracking-widest mb-1">{s.label}</span>
                                                                    <span className="text-sm font-black text-white font-mono leading-none group-hover:text-terminal-accent transition-colors">{val.toLocaleString()}</span>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>

                                                    {/* Attack Power Cluster */}
                                                    <div className="grid grid-cols-1 gap-2">
                                                        {[
                                                            { label: 'ATTACK POWER', val: selectedChar.char_att || selectedChar.ap_stats?.pad?.total || selectedChar.ap_stats?.physicalAttack?.total || 0 },
                                                            { label: 'MAGIC ATTACK', val: selectedChar.char_matt || selectedChar.ap_stats?.mad?.total || selectedChar.ap_stats?.magicalAttack?.total || 0 },
                                                        ].map(s => (
                                                            <div key={s.label} className="bg-terminal-accent/[0.02] border border-terminal-accent/10 rounded-xl px-5 py-4 flex items-center justify-between group hover:border-terminal-accent/30 transition-all">
                                                                <span className="text-[9px] font-black text-white/30 uppercase tracking-[0.2em]">{s.label}</span>
                                                                <span className="text-lg font-black text-terminal-accent font-mono leading-none drop-shadow-[0_0_8px_rgba(var(--terminal-accent),0.3)]">{s.val.toLocaleString()}</span>
                                                            </div>
                                                        ))}
                                                    </div>

                                                    {/* System Status Footer */}
                                                    <div className="mt-auto px-1 flex items-center justify-between text-[8px] font-black text-white/10 uppercase tracking-widest">
                                                        <span>Protocol v4.3.0</span>
                                                        <div className="flex gap-1.5">
                                                            <div className="w-1 h-1 bg-terminal-accent animate-pulse rounded-full" />
                                                            <span>Sync Active</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    ) : activeTab === "Legion & Collection" ? (
                                        <div className="w-full max-w-3xl space-y-8">
                                            {/* Legion Section */}
                                            <div className="bg-black/40 border border-white/5 rounded-lg p-6">
                                                <div className="text-[11px] font-bold text-terminal-cyan uppercase tracking-[.2em] mb-4">Legion Grid</div>
                                                <div className="flex items-center gap-6 mb-6">
                                                    <div className="flex-1">
                                                        <label className="text-[9px] text-terminal-muted uppercase tracking-widest block mb-1">Total Blocks</label>
                                                        <input
                                                            type="number"
                                                            value={legionBlocks}
                                                            onChange={e => setLegionBlocks(Math.max(0, parseInt(e.target.value) || 0))}
                                                            className="w-full bg-terminal-surface border border-white/10 text-terminal-text text-lg font-black px-4 py-3 rounded outline-none focus:border-terminal-cyan focus:ring-1 focus:ring-terminal-cyan/20"
                                                            placeholder="0"
                                                        />
                                                    </div>
                                                    <div className="flex-1">
                                                        <label className="text-[9px] text-terminal-muted uppercase tracking-widest block mb-1">Legion Bonuses</label>
                                                        {legionPreview ? (
                                                            <div className="text-sm font-mono">
                                                                {Object.entries(legionPreview)
                                                                    .filter(([k]) => k !== 'total_blocks' && k !== 'next_tier')
                                                                    .map(([k, v]) => (
                                                                        <span key={k} className="inline-block bg-terminal-cyan/10 text-terminal-cyan text-[10px] px-1.5 py-0.5 rounded mr-1 mb-1 border border-terminal-cyan/20">
                                                                            {k}: +{String(v)}%
                                                                        </span>
                                                                    ))}
                                                            </div>
                                                        ) : (
                                                            <span className="text-[10px] text-terminal-muted">Enter block count</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Collection Section */}
                                            <div className="bg-black/40 border border-white/5 rounded-lg p-6">
                                                <div className="text-[11px] font-bold text-terminal-green uppercase tracking-[.2em] mb-4">Collection</div>
                                                <div className="flex items-center gap-6">
                                                    <div className="flex-1">
                                                        <label className="text-[9px] text-terminal-muted uppercase tracking-widest block mb-1">Collection Score</label>
                                                        <input
                                                            type="number"
                                                            value={collectionScore}
                                                            onChange={e => setCollectionScore(Math.max(0, parseInt(e.target.value) || 0))}
                                                            className="w-full bg-terminal-surface border border-white/10 text-terminal-text text-lg font-black px-4 py-3 rounded outline-none focus:border-terminal-green focus:ring-1 focus:ring-terminal-green/20"
                                                            placeholder="0"
                                                        />
                                                    </div>
                                                    <div className="flex-1">
                                                        <label className="text-[9px] text-terminal-muted uppercase tracking-widest block mb-1">Collection Bonuses</label>
                                                        {collectionPreview ? (
                                                            <div className="text-sm font-mono">
                                                                {Object.entries(collectionPreview)
                                                                    .filter(([k]) => k !== 'total_score' && k !== 'next_tier')
                                                                    .map(([k, v]) => (
                                                                        <span key={k} className="inline-block bg-green-500/10 text-green-400 text-[10px] px-1.5 py-0.5 rounded mr-1 mb-1 border border-green-500/20">
                                                                            {k}: +{String(v)}%
                                                                        </span>
                                                                    ))}
                                                            </div>
                                                        ) : (
                                                            <span className="text-[10px] text-terminal-muted">Enter score</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <HyperStatsGrid
                                            hyperStats={selectedChar?.hyper_stats || []}
                                        />
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* RIGHT: Vectors */}
                        <div className="bg-[#111317] border border-white/10 rounded-2xl shadow-4xl sticky top-12 h-full">
                            <UpgradeVectors
                                sfParams={sfParams}
                                potParams={potParams}
                                bpParams={bpParams}
                                handleSfChange={handleSfChange}
                                handlePotChange={handlePotChange}
                                handleBpChange={handleBpChange}
                                selectedItem={selectedItem}
                                setSelectedItem={setSelectedItem}
                                itemLevel={itemLevel}
                                setItemLevel={setItemLevel}
                                handleCalculate={handleCalculate}
                                loading={loading}
                                result={result}
                                showBreakdown={showBreakdown}
                                setShowBreakdown={setShowBreakdown}
                                scannedChar={selectedChar}
                            />
                        </div>
                    </div>

                    {/* BOTTOM: Massive Item Registry */}
                    <div className="bg-[#111317] border border-white/5 rounded-3xl p-12 shadow-4xl ring-1 ring-white/10 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-terminal-cyan/50 to-transparent" />

                        <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-8 mb-12">
                            <div>
                                <h2 className="text-2xl font-black text-terminal-cyan uppercase tracking-[.6em] flex items-center gap-5">
                                    <span className="w-2 h-8 bg-terminal-cyan/40" />
                                    DATABASE REGISTRY
                                </h2>
                                <p className="text-white/20 text-xs mt-2 uppercase tracking-widest font-bold">Comprehensive Global Item Index // High-Tier Equipment Only</p>
                            </div>
                            <form onSubmit={handleCatalogSearch} className="flex gap-4 w-full xl:w-[600px] group">
                                <input
                                    type="text"
                                    placeholder="QUERY NAME / ASSET KEY / LEVEL..."
                                    value={catalogQuery}
                                    onChange={(e) => setCatalogQuery(e.target.value)}
                                    className="flex-1 bg-black/60 border border-white/10 text-terminal-text px-6 py-4 text-sm outline-none focus:border-terminal-cyan transition-all rounded-xl font-mono placeholder:text-white/5 group-hover:border-white/20"
                                />
                                <button type="submit" disabled={catalogSearching} className="bg-terminal-cyan text-black px-10 py-4 text-xs font-black hover:scale-105 active:scale-95 disabled:opacity-50 rounded-xl transition-all shadow-[0_0_40px_rgba(0,180,180,0.4)]">
                                    {catalogSearching ? "..." : "QUERY"}
                                </button>
                            </form>
                        </div>

                        {catalogResults.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6 animate-in fade-in duration-1000">
                                {catalogResults.map((item: any) => (
                                    <div key={item.item_id} onClick={() => handleSelectFromCatalog(item)}
                                        className="group relative flex items-center gap-6 p-6 bg-black/40 border border-white/5 hover:border-terminal-cyan/50 hover:bg-terminal-cyan/5 cursor-pointer transition-all duration-300 rounded-2xl overflow-visible ring-1 ring-white/5">

                                        <div className="absolute bottom-full mb-4 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 z-[999] transform">
                                            <ItemTooltipContent item={item} />
                                        </div>

                                        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />

                                        <div className="relative w-24 h-24 bg-[#0d0f12] p-4 flex items-center justify-center border border-white/10 group-hover:border-terminal-cyan/40 rounded-xl transition-all duration-500 group-hover:scale-110 shadow-2xl">
                                            <img src={item.image_url || `https://api-static.msu.io/itemimages/icon/${String(item.item_id).padStart(7, '0')}.png`}
                                                alt="" className="w-full h-full object-contain filter drop-shadow-[0_5px_15px_rgba(0,0,0,0.8)] contrast-110 group-hover:brightness-110"
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

                                        <div className="flex-1 min-w-0 relative z-10">
                                            <div className="text-lg font-black text-white truncate group-hover:text-terminal-cyan transition-colors uppercase tracking-tighter leading-tight mb-2">{item.name}</div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-[10px] bg-terminal-cyan/10 text-terminal-cyan px-2 py-0.5 rounded font-black tracking-widest border border-terminal-cyan/20">LV. {item.level}</span>
                                                <span className="text-[10px] text-white/20 uppercase tracking-[0.2em] font-black">ID: {item.item_id}</span>
                                            </div>
                                        </div>

                                        <div className="absolute top-2 right-4 text-terminal-cyan opacity-0 group-hover:opacity-100 transition-all font-black text-[10px] tracking-[.3em] uppercase">Select Unit</div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="py-32 flex flex-col items-center justify-center border border-dashed border-white/5 rounded-3xl opacity-20 grayscale bg-black/20">
                                <div className="text-[14px] font-black tracking-[0.8em] uppercase text-white mb-4">No Registry Matches Detected</div>
                                <p className="text-[10px] text-white font-bold opacity-50">INITIATE GLOBAL QUERY TO POPULATE RESULTS</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
