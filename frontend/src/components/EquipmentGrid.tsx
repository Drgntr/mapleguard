"use client";

import React from "react";
import ItemTooltipContent from "./ItemTooltipContent";

const EQUIPMENT_LAYOUT = [
    // Row 1
    { id: "RING1", label: "RING" },
    { id: "empty1" },
    { id: "HAT", label: "HAT" },
    { id: "empty2" },
    { id: "EMBLEM", label: "EMBLEM" },
    // Row 2
    { id: "RING2", label: "RING" },
    { id: "PENDANT1", label: "PENDANT" },
    { id: "FACE_ACCESSORY", label: "FACE ACC" },
    { id: "empty3" },
    { id: "BADGE", label: "BADGE" },
    // Row 3
    { id: "RING3", label: "RING" },
    { id: "PENDANT2", label: "PENDANT" },
    { id: "EYE_ACCESSORY", label: "EYE ACC" },
    { id: "EARRING", label: "EARRING" },
    { id: "empty4" },
    // Row 4
    { id: "RING4", label: "RING" },
    { id: "WEAPON", label: "WEAPON" },
    { id: "TOP", label: "TOP" },
    { id: "SHOULDER", label: "SHOULDER" },
    { id: "SECONDARY", label: "SUB WEAPON" },
    // Row 5
    { id: "POCKET", label: "POCKET" },
    { id: "BELT", label: "BELT" },
    { id: "BOTTOM", label: "BOTTOM" },
    { id: "GLOVES", label: "GLOVES" },
    { id: "CAPE", label: "CAPE" },
    // Row 6
    { id: "empty5" },
    { id: "empty6" },
    { id: "SHOES", label: "SHOES" },
    { id: "empty7" },
    { id: "empty8" },
    // Hidden Medal (since it's not in the screenshot's visible grid but needed)
    { id: "MEDAL", label: "MEDAL", hidden: true },
];

const ARCANE_LAYOUT = [
    { id: "ARCANE_VJ", label: "V. JOURNEY", multiplier: 227000 },
    { id: "ARCANE_CHUCHU", label: "CHU CHU", multiplier: 284000 },
    { id: "ARCANE_LACH", label: "LACHELEIN", multiplier: 341000 },
    { id: "ARCANE_ARCANA", label: "ARCANA", multiplier: 398000 },
    { id: "ARCANE_MORASS", label: "MORASS", multiplier: 455000 },
    { id: "ARCANE_ESFERA", label: "ESFERA", multiplier: 512000 },
];

const PETS_LAYOUT = [
    { id: "PET1", label: "PET 1" },
    { id: "PET2", label: "PET 2" },
    { id: "PET3", label: "PET 3" },
];

interface EquipmentGridProps {
    equippedItems: any[];
    onSelect?: (item: any) => void;
    selectedId?: string;
}

type TabType = "EQUIP" | "CASH" | "PET" | "ARCANE";

export default function EquipmentGrid({ equippedItems, onSelect, selectedId }: EquipmentGridProps) {
    const [activeTab, setActiveTab] = React.useState<TabType>("EQUIP");

    // Map API slots to our IDs
    const itemMap = new Map();
    equippedItems.forEach((item) => {
        if (item.cp_contribution) console.log(`[DEBUG] Item ${item.name} has CP: ${item.cp_contribution}`);
        if (item.item_type === "arcaneSymbol") return;

        if (activeTab === "CASH" && item.item_type !== "cashEquip") return;
        if (activeTab === "EQUIP" && item.item_type === "cashEquip") return;

        const slotStr = item.slot.toUpperCase().replace(/\s+/g, '_');
        let mapped = slotStr;

        // Comprehensive slot mapping for Navigator / Detail API slot keys
        if (slotStr === "CAP" || slotStr === "HAT") mapped = "HAT";
        if (slotStr === "CLOTHES" || slotStr === "TOP") mapped = "TOP";
        if (slotStr === "PANTS" || slotStr === "BOTTOM") mapped = "BOTTOM";
        if (slotStr === "SHOES") mapped = "SHOES";
        if (slotStr === "GLOVES") mapped = "GLOVES";
        if (slotStr === "CAPE") mapped = "CAPE";
        if (slotStr === "WEAPON") mapped = "WEAPON";
        if (slotStr === "SUBWEAPON" || slotStr === "SECONDARY") mapped = "SECONDARY";
        if (slotStr === "FACEACC" || slotStr === "FACEACCESSORY") mapped = "FACE_ACCESSORY";
        if (slotStr === "EYEACC" || slotStr === "EYEACCESSORY") mapped = "EYE_ACCESSORY";
        if (slotStr === "EARACC" || slotStr === "EARRING") mapped = "EARRING";
        if (slotStr === "SHOULDER") mapped = "SHOULDER";
        if (slotStr === "BELT") mapped = "BELT";
        if (slotStr === "POCKET") mapped = "POCKET";
        if (slotStr === "MEDAL") mapped = "MEDAL";
        if (slotStr === "BADGE") mapped = "BADGE";
        if (slotStr === "EMBLEM") mapped = "EMBLEM";
        if (slotStr === "RING" || slotStr === "RING1") mapped = "RING1";
        if (slotStr === "RING2") mapped = "RING2";
        if (slotStr === "RING3") mapped = "RING3";
        if (slotStr === "RING4") mapped = "RING4";
        if (slotStr === "PENDANT" || slotStr === "PENDANT1") mapped = "PENDANT1";
        if (slotStr === "PENDANT2") mapped = "PENDANT2";

        const found = EQUIPMENT_LAYOUT.find(l => l.id === mapped);
        if (found) itemMap.set(found.id, item);
        else if (item.item_type === "pet") {
            if (slotStr.includes("1")) itemMap.set("PET1", item);
            else if (slotStr.includes("2")) itemMap.set("PET2", item);
            else if (slotStr.includes("3")) itemMap.set("PET3", item);
            else {
                if (!itemMap.has("PET1")) itemMap.set("PET1", item);
                else if (!itemMap.has("PET2")) itemMap.set("PET2", item);
                else if (!itemMap.has("PET3")) itemMap.set("PET3", item);
            }
        }
    });

    const arcaneItems = equippedItems.filter(i => i.item_type === "arcaneSymbol");
    arcaneItems.forEach((item, idx) => {
        if (idx < ARCANE_LAYOUT.length) {
            itemMap.set(ARCANE_LAYOUT[idx].id, { ...item, multiplier: ARCANE_LAYOUT[idx].multiplier });
        }
    });

    const currentLayout = activeTab === "EQUIP" || activeTab === "CASH" ? EQUIPMENT_LAYOUT : activeTab === "ARCANE" ? ARCANE_LAYOUT : PETS_LAYOUT;

    return (
        <div className="bg-terminal-surface/30 border border-terminal-border rounded-xl p-8 w-fit mx-auto backdrop-blur-sm shadow-2xl origin-top overflow-visible relative z-20">
            {/* Tabs */}
            <div className="flex justify-center gap-12 mb-10 border-b border-white/5 pb-4">
                {(["EQUIP", "CASH", "PET", "ARCANE"] as TabType[]).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`text-[11px] font-black uppercase tracking-[0.3em] transition-all relative pb-2
                            ${activeTab === tab ? "text-white opacity-100" : "text-white/30 hover:text-white/60"}
                        `}
                    >
                        {tab}
                        {activeTab === tab && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-terminal-accent shadow-[0_0_10px_rgba(var(--terminal-accent),0.5)]" />
                        )}
                    </button>
                ))}
            </div>

            <div className={`grid gap-1 ${activeTab === "EQUIP" || activeTab === "CASH" ? "grid-cols-5" : "grid-cols-3 mx-auto w-fit"}`}>
                {currentLayout.map((slot: any, idx) => {
                    if (slot.hidden) return null;
                    if (slot.id && slot.id.startsWith("empty")) {
                        return <div key={idx} className="w-[65px] h-[65px] bg-black/5 border border-white/5 opacity-5" />;
                    }

                    const item = itemMap.get(slot.id);
                    const hasItem = !!item;
                    const isSelected = hasItem && selectedId === item.token_id;

                    const grade = item?.potential_grade ?? item?.potentialGrade ?? 0;
                    const sf = item?.starforce ?? item?.starForce ?? 0;

                    const isBig = activeTab === "PET" || activeTab === "ARCANE";
                    let specificBorder = "";
                    if (hasItem && item.item_type === "pet") {
                        const skills = (item.stats?.petSkills || item.pet_skills || []).map((s: any) => (typeof s === 'string' ? s : (s?.label || s?.name || "")).toLowerCase());
                        const nameLower = (item.name || "").toLowerCase();

                        const reallyHasMagnet = skills.some((s: string) => s.includes("magnet"));
                        const reallyHasBuff = skills.some((s: string) => s.includes("buff"));

                        if (reallyHasMagnet) {
                            specificBorder = "#00d832"; // Legendary Green
                        } else if (reallyHasBuff) {
                            specificBorder = "#ffb400"; // Unique Yellow
                        } else {
                            if (nameLower.includes("plumpy")) specificBorder = "#00d832";
                            else if (nameLower.includes("bird") || nameLower.includes("cat") || nameLower.includes("pig") || nameLower.includes("unit") || nameLower.includes("pet")) specificBorder = "#ffb400";
                        }
                    }

                    return (
                        <div key={idx} className="relative group">
                            <div
                                onClick={() => hasItem && onSelect?.(item)}
                                className={`${isBig ? "w-[90px] h-[90px]" : "w-[65px] h-[65px]"} border flex items-center justify-center overflow-hidden transition-all duration-300 cursor-pointer relative shadow-inner
                  ${hasItem ? "bg-[#1f2128]" : "bg-black/40 border-white/5 opacity-50"}
                  ${isSelected ? "ring-1 ring-terminal-accent ring-inset scale-105 z-10" : ""}
                `}
                                style={{
                                    borderColor: specificBorder ? specificBorder : (hasItem ? (
                                        grade === 4 ? "#00ff00" :
                                            grade === 3 ? "#ffff00" :
                                                grade === 2 ? "#d646ff" :
                                                    grade === 1 ? "#00bbff" : "rgba(255,255,255,0.1)"
                                    ) : "rgba(255,255,255,0.05)")
                                }}
                            >
                                {!hasItem && slot.label && (
                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <span className={`${isBig ? "text-[12px]" : "text-[10px]"} font-black text-white/10 uppercase tracking-tighter text-center leading-none px-1`}>{slot.label}</span>
                                    </div>
                                )}
                                {hasItem ? (
                                    <div className="relative w-full h-full flex items-center justify-center p-2">
                                        <img src={item.image_url || (item.item_id || item.itemId ? `https://api-static.msu.io/itemimages/icon/${String(item.item_id || item.itemId).padStart(7, '0')}.png` : '')}
                                            alt={slot.id}
                                            className={`${isBig ? "w-14 h-14" : "w-10 h-10"} object-contain filter drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]`}
                                            onError={(e) => {
                                                const t = e.target as HTMLImageElement;
                                                if (t.src && !t.src.includes('0000000')) {
                                                    const id = String(item.item_id || item.itemId);
                                                    if (t.src.includes('icon/0')) {
                                                        t.src = "https://api-static.msu.io/itemimages/icon/0000000.png";
                                                        t.style.opacity = "0.2";
                                                    } else {
                                                        t.src = `https://api-static.msu.io/itemimages/icon/0${id}.png`;
                                                    }
                                                }
                                            }} />

                                        <div className="absolute bottom-1 right-1 w-4 h-4 bg-red-600 rounded flex items-center justify-center shadow-lg border border-red-400/50">
                                            <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" /></svg>
                                        </div>

                                        {(sf > 0 || item.item_type === "arcaneSymbol") && (
                                            <div className={`absolute top-1 left-1 bg-black/40 rounded px-1 ${isBig ? "text-[10px]" : "text-[7px]"} font-black text-yellow-400`}>
                                                ★{sf || item.level}
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="w-full h-full bg-grid-pattern opacity-[0.05]" />
                                )}
                            </div>

                            {/* TOOLTIP */}
                            {hasItem && (
                                <div className={`absolute left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 z-[999] transform group-hover:translate-y-[-10px]
                                    ${idx < 10 ? "top-full mt-6" : "bottom-full mb-6"}
                                `}>
                                    <ItemTooltipContent item={item} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div >
    );
}
