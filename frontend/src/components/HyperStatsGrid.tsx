"use client";

import React from "react";

interface HyperStatsGridProps {
    hyperStats: Record<string, number> | any[];
}

const STAT_LABELS: Record<string, string> = {
    str: "STR",
    dex: "DEX",
    int: "INT",
    luk: "LUK",
    maxHp: "HP",
    maxMp: "MP",
    dfTfPp: "DF/TF/PP",
    criticalRate: "CRIT RATE",
    criticalDamage: "CRIT DMG",
    ignoreDefence: "IED",
    defense: "DEF",
    damage: "DAMAGE",
    bossMonsterDamage: "BOSS DMG",
    normalMonsterDamage: "NORMAL DMG",
    statusResistance: "STATUS RES",
    knockbackResistance: "STANCE",
    attackAndMagicAttack: "ATT / M.ATT",
    bonusExp: "EXP",
    arcaneForce: "ARCANE FORCE",
    mesoDropRate: "MESO DROP",
    itemDropRate: "ITEM DROP",
};

export default function HyperStatsGrid({ hyperStats }: HyperStatsGridProps) {
    const statsArray = Array.isArray(hyperStats)
        ? hyperStats.map(s => [s.stat_type || s.id, s.level || 0])
        : Object.entries(hyperStats);

    const filtered = statsArray.filter(([k, v]) => STAT_LABELS[k] && Number(v) > 0);

    return (
        <div className="w-full max-w-2xl mx-auto">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                {filtered.length > 0 ? (
                    filtered.map(([key, level]: any) => (
                        <div key={key} className="bg-black/20 border border-white/5 p-4 rounded-xl group hover:border-terminal-accent/30 transition-all relative overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                            <div className="relative z-10 flex flex-col gap-3">
                                <span className="text-[10px] text-white/40 uppercase tracking-[.2em] font-black group-hover:text-terminal-accent transition-colors">
                                    {STAT_LABELS[key] || key}
                                </span>
                                <div className="flex items-end justify-between">
                                    <span className="text-sm font-black text-white font-mono uppercase tracking-tighter">
                                        LVL {level}
                                    </span>
                                    <div className="flex gap-0.5 pb-1">
                                        {Array.from({ length: 10 }).map((_, i) => (
                                            <div key={i} className={`w-1 h-3 rounded-full transition-all duration-500 ${i < level ? "bg-terminal-accent shadow-[0_0_8px_rgba(var(--terminal-accent),0.3)]" : "bg-white/5"}`} />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-20 flex flex-col items-center justify-center border border-dashed border-white/5 rounded-2xl opacity-20 grayscale">
                        <div className="text-[11px] font-black tracking-[.4em] uppercase text-white">NO STAT DATA DETECTED</div>
                    </div>
                )}
            </div>
        </div>
    );
}
