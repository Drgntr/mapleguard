"use client";

import React, { useState, useEffect } from "react";

const GRADE_LABELS: Record<number, { label: string; color: string }> = {
    0: { label: "NORMAL", color: "text-gray-400" },
    1: { label: "RARE", color: "text-blue-400" },
    2: { label: "EPIC", color: "text-purple-400" },
    3: { label: "UNIQUE", color: "text-yellow-400" },
    4: { label: "LEGENDARY", color: "text-green-400" },
};

// Maps frontend slot names to backend slot keys
const SLOT_MAP: Record<string, string> = {
    HAT: "hat", CAP: "hat",
    TOP: "top", CLOTHES: "top",
    BOTTOM: "bottom", PANTS: "bottom",
    SHOES: "shoes",
    GLOVES: "gloves",
    CAPE: "cape",
    WEAPON: "weapon",
    SECONDARY: "secondary", SUBWEAPON: "secondary",
    SHOULDER: "shoulder",
    FACE_ACCESSORY: "face", FACEACC: "face",
    EYE_ACCESSORY: "eye", EYEACC: "eye",
    EARRING: "earring", EARACC: "earring",
    RING1: "ring", RING2: "ring", RING3: "ring", RING4: "ring",
    PENDANT1: "pendant", PENDANT2: "pendant",
    BELT: "belt",
    POCKET: "pocket",
    BADGE: "badge",
    EMBLEM: "emblem",
};

const SLOT_OPTIONS = [
    { value: "weapon", label: "WEAPON" },
    { value: "hat", label: "HAT" },
    { value: "top", label: "TOP" },
    { value: "bottom", label: "BOTTOM" },
    { value: "shoes", label: "SHOES" },
    { value: "gloves", label: "GLOVES" },
    { value: "cape", label: "CAPE" },
    { value: "shoulder", label: "SHOULDER" },
    { value: "face", label: "FACE ACC" },
    { value: "eye", label: "EYE ACC" },
    { value: "earring", label: "EARRING" },
    { value: "ring", label: "RING" },
    { value: "pendant", label: "PENDANT" },
    { value: "belt", label: "BELT" },
    { value: "emblem", label: "EMBLEM" },
    { value: "secondary", label: "SECONDARY" },
    { value: "pocket", label: "POCKET" },
    { value: "badge", label: "BADGE" },
];

interface UpgradeSuggestionsProps {
    equippedItems: any[];
}

export default function UpgradeSuggestions({ equippedItems }: UpgradeSuggestionsProps) {
    const [selectedSlot, setSelectedSlot] = useState("weapon");
    const [upgrades, setUpgrades] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [totalFound, setTotalFound] = useState(0);

    // Find the currently equipped item for the selected slot
    const currentItem = React.useMemo(() => {
        const slotKey = selectedSlot;
        return equippedItems.find((item) => {
            const mapped = SLOT_MAP[item.slot?.toUpperCase()] || item.slot?.toLowerCase();
            return mapped === slotKey;
        });
    }, [equippedItems, selectedSlot]);

    useEffect(() => {
        if (!selectedSlot) return;
        const currentSf = currentItem?.starforce || 0;
        const currentGrade = currentItem?.potential_grade || 0;

        setLoading(true);
        setUpgrades([]);
        fetch(`/api/items/upgrades?slot=${selectedSlot}&current_sf=${currentSf}&current_grade=${currentGrade}&limit=12`)
            .then((res) => res.json())
            .then((data) => {
                setUpgrades(data.items || []);
                setTotalFound(data.total_found || 0);
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [selectedSlot, currentItem?.starforce, currentItem?.potential_grade]);

    const formatPrice = (priceWei: string) => {
        try {
            const neso = parseInt(priceWei) / 1e18;
            if (neso >= 1_000_000) return `${(neso / 1_000_000).toFixed(1)}M`;
            if (neso >= 1_000) return `${(neso / 1_000).toFixed(0)}K`;
            return neso.toFixed(0);
        } catch {
            return "?";
        }
    };

    return (
        <div className="w-full mt-8">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-1.5 h-6 bg-terminal-accent/60 rounded-full" />
                    <h3 className="text-[11px] font-black text-white/60 uppercase tracking-[0.3em]">
                        MARKETPLACE UPGRADES
                    </h3>
                </div>
                <select
                    value={selectedSlot}
                    onChange={(e) => setSelectedSlot(e.target.value)}
                    className="bg-black/60 border border-white/10 text-white text-[11px] font-black uppercase tracking-wider px-4 py-2 rounded-lg outline-none focus:border-terminal-accent cursor-pointer"
                >
                    {SLOT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
                </select>
            </div>

            {/* Current item reference */}
            {currentItem && (
                <div className="mb-3 flex items-center gap-3 px-3 py-2 bg-white/[0.02] border border-white/5 rounded-lg">
                    <span className="text-[9px] font-black text-white/20 uppercase tracking-widest">EQUIPPED:</span>
                    <span className="text-[11px] font-bold text-white/60">{currentItem.name || "Unknown"}</span>
                    {currentItem.starforce > 0 && (
                        <span className="text-[10px] font-bold text-yellow-400">★{currentItem.starforce}</span>
                    )}
                    {currentItem.potential_grade > 0 && (
                        <span className={`text-[10px] font-bold ${GRADE_LABELS[currentItem.potential_grade]?.color}`}>
                            {GRADE_LABELS[currentItem.potential_grade]?.label}
                        </span>
                    )}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-8">
                    <div className="w-5 h-5 border-2 border-terminal-accent/30 border-t-terminal-accent rounded-full animate-spin" />
                    <span className="ml-3 text-[10px] font-black text-white/20 uppercase tracking-widest">SCANNING MARKETPLACE...</span>
                </div>
            ) : upgrades.length === 0 ? (
                <div className="py-8 text-center border border-dashed border-white/5 rounded-xl">
                    <div className="text-[11px] font-black text-white/15 uppercase tracking-widest">
                        NO UPGRADES FOUND FOR THIS SLOT
                    </div>
                    <div className="text-[9px] text-white/10 mt-1">Your current equipment may already be optimal</div>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {upgrades.map((item, idx) => {
                            const grade = GRADE_LABELS[item.potential_grade] || GRADE_LABELS[0];
                            const bgrade = GRADE_LABELS[item.bonus_potential_grade] || GRADE_LABELS[0];
                            return (
                                <div
                                    key={item.token_id || idx}
                                    className="group flex items-center gap-3 p-3 bg-black/30 border border-white/5 rounded-lg hover:border-terminal-accent/30 hover:bg-terminal-accent/[0.03] transition-all cursor-pointer"
                                >
                                    <div className="w-12 h-12 bg-black/40 border border-white/10 rounded-lg flex items-center justify-center p-1.5 flex-shrink-0">
                                        <img
                                            src={item.image_url || `https://api-static.msu.io/itemimages/icon/${String(item.item_id || 0).padStart(7, "0")}.png`}
                                            alt=""
                                            className="w-full h-full object-contain"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.opacity = "0.1";
                                            }}
                                        />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-[11px] font-bold text-white truncate">{item.name}</div>
                                        <div className="flex items-center gap-2 mt-1">
                                            {item.starforce > 0 && (
                                                <span className="text-[9px] font-bold text-yellow-400">
                                                    ★{item.starforce}
                                                    {item.sf_gain > 0 && (
                                                        <span className="text-terminal-accent ml-0.5">(+{item.sf_gain})</span>
                                                    )}
                                                </span>
                                            )}
                                            <span className={`text-[9px] font-bold ${grade.color}`}>
                                                {grade.label}
                                                {item.grade_gain > 0 && (
                                                    <span className="text-terminal-accent ml-0.5">(+{item.grade_gain})</span>
                                                )}
                                            </span>
                                            {item.bonus_potential_grade > 0 && (
                                                <span className={`text-[8px] font-bold ${bgrade.color} opacity-60`}>
                                                    B:{bgrade.label}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="text-right flex-shrink-0">
                                        <div className="text-[11px] font-black text-terminal-accent font-mono">
                                            {formatPrice(item.price_wei)}
                                        </div>
                                        <div className="text-[8px] text-white/15 font-bold">NESO</div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {totalFound > upgrades.length && (
                        <div className="text-center mt-3 text-[9px] text-white/15 font-bold uppercase tracking-widest">
                            +{totalFound - upgrades.length} more upgrades found
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
