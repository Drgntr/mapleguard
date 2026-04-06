import React, { useState, useEffect } from 'react';

interface ItemTooltipProps {
    item: any;
}

const POT_GRADE_STYLES: Record<number, any> = {
    0: { label: 'NORMAL', border: 'border-gray-500', text: 'text-gray-400', bg: 'bg-gray-500/20' },
    1: { label: 'RARE', border: 'border-blue-500', text: 'text-blue-400', bg: 'bg-blue-500/20', icon: 'R' },
    2: { label: 'EPIC', border: 'border-purple-500', text: 'text-purple-400', bg: 'bg-purple-500/20', icon: 'E' },
    3: { label: 'UNIQUE', border: 'border-yellow-500', text: 'text-yellow-400', bg: 'bg-yellow-500/20', icon: 'U' },
    4: { label: 'LEGENDARY', border: 'border-green-500', text: 'text-green-400', bg: 'bg-green-500/20', icon: 'L' },
};

export default function ItemTooltipContent({ item }: ItemTooltipProps) {
    const [details, setDetails] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!item?.token_id || item.item_type === "arcaneSymbol" || item.item_type === "pet") return;
        setDetails(null);
        setLoading(true);
        fetch(`/api/items/lookup?query=${encodeURIComponent(item.token_id)}`)
            .then(res => res.json())
            .then(data => {
                if (data.item) setDetails(data.item);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [item?.token_id]);

    if (!item) return null;

    const slotLabel = item.slot?.toUpperCase() || "ITEM";
    const d = { ...details, ...item };
    const grade = d.potential_grade || 0;
    const style = POT_GRADE_STYLES[grade] || POT_GRADE_STYLES[0];
    const starforce = d.starforce || 0;
    const name = d.name || slotLabel || "Unknown Asset";
    const level = d.required_level || d.level || 150;
    const stats = d.stats || {};
    const itemId = String(d.item_id || '0000000');
    // If analyzed CP contribution exists, use it. Otherwise display +0
    const cpContribution = d.cp_contribution || d.cp_gain || 0;
    // DEBUG: trace CP data flow (remove after confirming)
    if (typeof window !== 'undefined') {
        console.log(`[CP DEBUG] ${name}: item.cp=${item.cp_contribution}, details.cp=${details?.cp_contribution}, merged.cp=${d.cp_contribution}, final=${cpContribution}`);
    }

    const renderStat = (label: string, value: any, baseFallback?: number) => {
        if (!value && value !== 0) return null;
        let total = 0;
        let baseVal = 0;

        // API sometimes returns { total: X, base: Y, enhance: Z }
        if (typeof value === 'object' && value !== null) {
            total = typeof value.total === 'number' ? value.total : parseInt(String(value.total || 0));
            baseVal = typeof value.base === 'number' ? value.base : total;
        } else {
            total = typeof value === 'number' ? value : parseInt(String(value));
            if (isNaN(total)) return null;
            baseVal = typeof baseFallback === 'number' ? baseFallback : total;
        }

        if (total === 0 && baseVal === 0) return null;

        const bonus = total - baseVal;
        return (
            <div className="flex text-white text-[12px] leading-tight mb-0.5 whitespace-nowrap">
                <span className="opacity-95 text-white/50 font-medium">{label} : </span><span className={`ml-1 font-bold ${bonus > 0 ? "text-terminal-accent" : "text-white"}`}>+{total}</span>
                {bonus > 0 && <span className="text-white/20 ml-1.5 text-[11px] font-normal tracking-tight font-mono">({baseVal} <span className="text-terminal-accent">+{bonus}</span>)</span>}
            </div>
        );
    };

    return (
        <div className="bg-[#111]/98 border-[2px] border-[#444] rounded-sm flex flex-col w-[300px] shadow-[0_25px_80px_rgba(0,0,0,0.95)] font-sans backdrop-blur-xl">
            {/* Stars rendering with groups of 5 */}
            <div className="bg-black/80 p-2.5 pb-2 flex flex-col items-center border-b border-white/5">
                <div className="flex flex-wrap justify-center max-w-[240px]">
                    {Array.from({ length: Math.max(15, starforce) }).map((_, i) => (
                        <span key={i} className={`text-[15px] leading-none ${(i + 1) % 5 === 0 ? "mr-3.5" : "mr-[1px]"} ${i < starforce ? "text-yellow-400 drop-shadow-[0_0_10px_rgba(250,204,21,0.5)]" : "text-white/5"}`}>
                            {i < starforce ? "★" : "☆"}
                        </span>
                    ))}
                </div>
            </div>

            <div className="p-5 pt-3 border-b border-gray-700/50 flex flex-col items-center text-center">
                <h3 className={`text-[17px] font-black tracking-tight mb-1 drop-shadow-md ${grade >= 2 ? "text-terminal-accent" : "text-white"}`}>{name}</h3>
                <div className="text-white/30 text-[10px] mt-1.5 uppercase font-black tracking-widest border border-white/10 px-2 py-0.5 rounded-full">{style.label} PROTOCOL</div>
            </div>

            <div className="p-4 flex gap-4 border-b border-gray-700/40">
                <div className="relative w-[90px] h-[90px] bg-gray-900 border-2 rounded-xl flex items-center justify-center p-2 shadow-inner border-gray-800">
                    <img src={d.image_url || `https://api-static.msu.io/itemimages/icon/${itemId.padStart(7, '0')}.png`} alt="" className="w-14 h-14 object-contain filter drop-shadow-2xl" />
                </div>
                <div className="flex-1 flex flex-col justify-center gap-3">
                    <div className="border-b border-white/5 pb-2">
                        <div className="text-[9px] text-white/30 font-black uppercase tracking-widest mb-1">Combat Rating Upgrade</div>
                        <div className={`text-3xl font-black font-mono ${cpContribution > 0 ? "text-terminal-accent" : "text-white/10"}`}>
                            +{cpContribution.toLocaleString()}
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[9px] uppercase font-black font-mono">
                        <div className="flex justify-between items-center text-white/40"><span>REQ LVL:</span> <span className="text-white">{level}</span></div>
                    </div>
                </div>
            </div>

            <div className="p-4 py-3 space-y-1 bg-black/40 border-b border-gray-700/40">
                <div className="text-white/20 text-[10px] mb-2 font-black uppercase tracking-[0.3em] border-l-2 border-white/5 pl-3">SYSTEM STATS</div>
                {renderStat("STR", stats.str || stats.base_str || stats.str_stat, stats.base_str)}
                {renderStat("DEX", stats.dex || stats.base_dex, stats.base_dex)}
                {renderStat("LUK", stats.luk || stats.base_luk, stats.base_luk)}
                {renderStat("INT", stats.int || stats.base_int || stats.int_stat, stats.base_int)}
                {renderStat("MAX HP", stats.hp || stats.maxHp || stats.base_hp, stats.base_hp)}
                {renderStat("ATTACK POWER", stats.pad || stats.att, stats.base_pad)}
                {renderStat("MAGIC ATT", stats.mad || stats.m_att, stats.base_mad)}
            </div>

            <div className="p-5 py-4 border-b border-gray-800 bg-gradient-to-r from-transparent via-white/[0.01] to-transparent">
                <div className="flex items-center gap-2 mb-3 font-black text-[11px] uppercase tracking-widest">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black ${style.bg}`}>{style.icon || "N"}</div>
                    <span className={`${style.text}`}>Primary Potential</span>
                </div>
                <div className="space-y-1.5 mb-6">
                    {d.potential ? Object.values(d.potential).map((opt: any, i) => {
                        const label = typeof opt === 'string' ? opt : opt?.label;
                        return label ? <div key={`pot-${i}`} className="text-white text-[12px] font-bold pl-2 border-l border-white/10">{label}</div> : null;
                    }) : <div className="text-white/20 text-[12px] font-bold pl-2 italic">NO PROTOCOL DATA</div>}
                </div>

                {d.bonus_potential && Object.keys(d.bonus_potential).length > 0 && (
                    <div className="mt-8 pt-4 border-t border-white/5">
                        <div className="flex items-center gap-2 mb-3 font-black text-[11px] uppercase tracking-widest">
                            <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.3)]">B</div>
                            <span className="text-blue-400">Bonus Potential</span>
                        </div>
                        <div className="space-y-1.5">
                            {Object.values(d.bonus_potential).map((opt: any, i) => {
                                const label = typeof opt === 'string' ? opt : opt?.label;
                                return label ? <div key={`bpot-${i}`} className="text-white text-[12px] font-bold pl-2 border-l border-blue-500/30">{label}</div> : null;
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
