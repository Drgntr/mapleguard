"use client";

import { useState, useMemo } from "react";
import { useCharacters, useFloorPrices, useCharacterDetail, useEnrichedListings, useEnrichedCharDetail, useRecentSales } from "@/hooks/useMarketData";

const CLASS_COLORS: Record<string, string> = {
  Archer: "text-terminal-green",
  Magician: "text-terminal-purple",
  Pirate: "text-terminal-cyan",
  Thief: "text-terminal-red",
  Warrior: "text-terminal-yellow",
};

const CLASS_BG: Record<string, string> = {
  Archer: "bg-terminal-green/10 border-terminal-green/20",
  Magician: "bg-terminal-purple/10 border-terminal-purple/20",
  Pirate: "bg-terminal-cyan/10 border-terminal-cyan/20",
  Thief: "bg-terminal-red/10 border-terminal-red/20",
  Warrior: "bg-terminal-yellow/10 border-terminal-yellow/20",
};

// Sub-class mapping (simplified for UI)
const SUBCLASSES: Record<string, string[]> = {
  Warrior: ["Hero", "Paladin", "Dark Knight", "Dawn Warrior", "Mihile", "Aran", "Demon Slayer", "Demon Avenger", "Blaster", "Kaiser", "Adele", "Hayato", "Zero"],
  Magician: ["Fire/Poison", "Ice/Lightning", "Bishop", "Blaze Wizard", "Evan", "Luminous", "Battle Mage", "Kinesis", "Illium", "Lara"],
  Archer: ["Bowmaster", "Marksman", "Pathfinder", "Wind Archer", "Mercedes", "Cain"],
  Thief: ["Night Lord", "Shadower", "Dual Blade", "Night Walker", "Phantom", "Xenon", "Cadena", "HoYoung"],
  Pirate: ["Buccaneer", "Corsair", "Cannon Master", "Thunder Breaker", "Shade", "Mechanic", "Angelic Buster", "Ark"],
};

const FLOOR_LEVELS = [65, 120, 140, 160, 170, 180, 190, 200, 210, 220, 230, 240];

const ARCANE_TIER_COLORS: Record<string, string> = {
  none: "text-terminal-muted",
  absolab: "text-terminal-text",
  arcane_umbra: "text-terminal-yellow",
  arcane_full: "text-terminal-green",
  genesis_partial: "text-terminal-cyan",
  genesis_full: "text-terminal-green",
  eternal_partial: "text-terminal-purple",
  eternal_full: "text-terminal-purple",
};

const ARCANE_BG: Record<string, string> = {
  none: "bg-white/5 border-white/10",
  absolab: "bg-terminal-text/10 border-terminal-text/20",
  arcane_umbra: "bg-terminal-yellow/10 border-terminal-yellow/20",
  arcane_full: "bg-terminal-green/10 border-terminal-green/20",
  genesis_partial: "bg-terminal-cyan/10 border-terminal-cyan/20",
  genesis_full: "bg-terminal-green/10 border-terminal-green/20",
  eternal_partial: "bg-terminal-purple/10 border-terminal-purple/20",
  eternal_full: "bg-terminal-purple/10 border-terminal-purple/20",
};

function abilityColor(total: number): string {
  if (total >= 12) return "text-terminal-red font-black";
  if (total >= 8) return "text-terminal-yellow font-bold";
  if (total >= 4) return "text-terminal-cyan";
  return "text-terminal-muted";
}

function arcaneBadge(tier: string): string {
  const label = tier.replace("_", " ").toUpperCase();
  return (
    <span
      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${ARCANE_BG[tier] || "bg-white/5"} ${ARCANE_TIER_COLORS[tier] || "text-terminal-muted"}`}
    >
      {label}
    </span>
  );
}

export default function CharactersPage() {
  const [page, setPage] = useState(1);
  const [classFilter, setClassFilter] = useState("all_classes");
  const [jobFilter, setJobFilter] = useState("all_jobs");
  const [levelMin, setLevelMin] = useState(0);
  const [levelMax, setLevelMax] = useState(300);
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const [view, setView] = useState<"explore" | "underpriced" | "recent-sales">("underpriced");
  const [sort, setSort] = useState("fair_vs_price");

  const { data, isLoading } = useCharacters(page, 135, classFilter, jobFilter, levelMin, levelMax);
  const { data: floorData } = useFloorPrices();
  const { data: detailData } = useCharacterDetail(selectedTokenId);

  // Enriched listing hooks
  const charFilter = classFilter === "all_classes" ? "" : classFilter;
  const { data: enrichedData, isLoading: enrichedLoading } = useEnrichedListings(
    page, 135, sort, charFilter, view === "underpriced" ? "enriched" : ""
  );
  const { data: salesData } = useRecentSales(50, charFilter);

  const chars = data?.characters || [];
  const enriched = enrichedData?.listings || [];
  const enrichedTotal = enrichedData?.total || 0;
  const sales = salesData?.sales || [];
  const floors = floorData?.floor_prices || {};
  const detail = detailData?.character;

  const currentSubclasses = classFilter === "all_classes" ? [] : SUBCLASSES[classFilter] || [];
  const displayListings = view === "explore" ? chars : view === "recent-sales" ? sales : enriched;
  const displayTotal = view === "explore" ? data?.count : enrichedTotal;
  const displayLoading = view === "underpriced" ? enrichedLoading : isLoading;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
            CHARACTER MARKET
          </h2>
          <p className="text-xs font-mono text-terminal-muted mt-1">
            Real-time character listings and protocol analysis
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-mono font-bold text-terminal-accent">
            {data?.count?.toLocaleString() || "---"}
          </p>
          <p className="text-[10px] font-mono text-terminal-muted uppercase tracking-tighter">Listed in Marketplace</p>
        </div>
      </div>

      {/* Filters: Primary Class */}
      <div className="space-y-4">
        {/* View Toggle */}
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] font-mono text-terminal-muted w-12">VIEW:</span>
          {(["underpriced", "explore", "recent-sales"] as const).map((v) => (
            <button
              key={v}
              onClick={() => { setView(v); setPage(1); }}
              className={`px-3 py-1.5 text-xs font-mono rounded border transition-all ${view === v
                ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                : "border-terminal-border text-terminal-muted hover:text-terminal-text"
                }`}
            >
              {v === "underpriced" ? "UNDERPRICED" : v === "explore" ? "EXPLORE ALL" : "RECENT SALES"}
            </button>
          ))}
        </div>

        {/* Sort buttons */}
        {view !== "recent-sales" && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-[10px] font-mono text-terminal-muted w-12">SORT:</span>
            {[
              ["fair_vs_price", "FAIR %"],
              ["price_asc", "PRICE ↑"],
              ["price_desc", "PRICE ↓"],
              ["level_asc", "LV ↑"],
              ["gear_desc", "GEAR ↓"],
            ].map(([k, l]) => (
              <button
                key={k}
                onClick={() => { setSort(k); setPage(1); }}
                className={`px-3 py-1.5 text-[11px] font-mono rounded border transition-all ${sort === k
                  ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                  : "border-terminal-border text-terminal-muted hover:text-terminal-text"
                  }`}
              >
                {l}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] font-mono text-terminal-muted w-16">CLASS:</span>
          {["all_classes", "Archer", "Magician", "Pirate", "Thief", "Warrior"].map(
            (cls) => (
              <button
                key={cls}
                onClick={() => {
                  setClassFilter(cls);
                  setJobFilter("all_jobs");
                  setPage(1);
                }}
                className={`px-3 py-1.5 text-xs font-mono rounded border transition-all ${classFilter === cls
                  ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                  : "border-terminal-border text-terminal-muted hover:border-terminal-border-bright hover:text-terminal-text"
                  }`}
              >
                {cls === "all_classes" ? "ALL CLASSES" : cls.toUpperCase()}
              </button>
            )
          )}
        </div>

        {/* Sub-class Filters */}
        {currentSubclasses.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center pb-2 border-b border-white/5">
            <span className="text-[10px] font-mono text-terminal-muted w-16">SUB-JOB:</span>
            <button
              onClick={() => { setJobFilter("all_jobs"); setPage(1); }}
              className={`px-2 py-1 text-[10px] font-mono rounded border transition-all ${jobFilter === "all_jobs" ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10" : "border-terminal-border text-terminal-muted"
                }`}
            >
              ALL
            </button>
            {currentSubclasses.map((sj) => (
              <button
                key={sj}
                onClick={() => {
                  setJobFilter(sj);
                  setPage(1);
                }}
                className={`px-2 py-1 text-[10px] font-mono rounded border transition-all ${jobFilter === sj
                  ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                  : "border-terminal-border text-terminal-muted hover:text-terminal-text"
                  }`}
              >
                {sj.toUpperCase()}
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] font-mono text-terminal-muted w-16">LEVELS:</span>
          {[
            [0, 300, "ALL LV"],
            [65, 119, "65-119"],
            [120, 139, "120-139"],
            [140, 159, "140-159"],
            [160, 199, "160-199"],
            [200, 219, "200-219"],
            [220, 229, "220-229"],
            [230, 239, "230-239"],
            [240, 300, "240+"],
          ].map(([min, max, label]) => (
            <button
              key={label as string}
              onClick={() => {
                setLevelMin(min as number);
                setLevelMax(max as number);
                setPage(1);
              }}
              className={`px-3 py-1.5 text-[11px] font-mono rounded border transition-all ${levelMin === min && levelMax === max
                ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                : "border-terminal-border text-terminal-muted hover:text-terminal-text"
                }`}
            >
              {label as string}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Characters table */}
        <div className="xl:col-span-2 panel">
          <div className="panel-header">
            <span className="panel-title">
              {view === "underpriced" ? "UNDERPRICED LISTINGS" : view === "recent-sales" ? "RECENT SALES" : "EXPLORER"}
            </span>
            <span className="text-[10px] font-mono text-terminal-muted uppercase">
              {(view === "explore" ? data?.count : enrichedTotal)?.toLocaleString?.() || "0"} results
            </span>
          </div>
          <div className="max-h-[600px] overflow-y-auto">
            {displayLoading ? (
              <div className="p-12 text-center">
                <div className="w-8 h-8 border-2 border-terminal-accent border-t-transparent animate-spin rounded-full mx-auto mb-4" />
                <div className="text-terminal-accent font-mono text-xs uppercase tracking-widest animate-pulse">Loading...</div>
              </div>
            ) : displayListings.length === 0 ? (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm uppercase">
                Zero Matches Found In Archive
              </div>
            ) : view === "recent-sales" ? (
              <table className="data-table">
                <thead className="sticky top-0 bg-terminal-panel z-10">
                  <tr>
                    <th>TOKEN ID</th>
                    <th>NAME</th>
                    <th>CLASS</th>
                    <th>LEVEL</th>
                    <th>SELL PRICE</th>
                    <th>ARCANE</th>
                    <th>ABILITY</th>
                    <th>GEAR</th>
                    <th>DATE</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.map((sale: any) => (
                    <tr key={sale.tx_hash} className="text-[11px]">
                      <td className="text-terminal-muted font-mono text-[9px]">{sale.token_id?.slice(0, 10)}...</td>
                      <td className="text-terminal-text font-medium">{sale.class_name}</td>
                      <td>
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${CLASS_BG[sale.class_name] || "bg-white/5"} ${CLASS_COLORS[sale.class_name] || "text-white"}`}>
                          {sale.class_name?.toUpperCase()}
                        </span>
                      </td>
                      <td className={`font-mono ${sale.level >= 240 ? "text-terminal-red font-bold" : "text-terminal-text"}`}>
                        LV.{sale.level}
                      </td>
                      <td className="text-terminal-accent font-bold">{sale.price?.toLocaleString()}</td>
                      <td className="text-terminal-muted">{sale.arcane_force}</td>
                      <td className={abilityColor(sale.ability_total)}>{sale.ability_total}</td>
                      <td className="text-terminal-text">{sale.gear_score?.toFixed(0)}</td>
                      <td className="text-terminal-muted text-[10px]">{sale.sale_date?.split("T")[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="data-table">
                <thead className="sticky top-0 bg-terminal-panel z-10">
                  <tr>
                    <th>NAME</th>
                    <th>CLASS</th>
                    <th>LEVEL</th>
                    {view === "underpriced" ? (
                      <>
                        <th>ARCANE</th>
                        <th>ABILITY</th>
                        <th>PRICE (NESO)</th>
                        <th>FAIR VALUE</th>
                        <th>VS FAIR</th>
                        <th>GEAR</th>
                      </>
                    ) : (
                      <>
                        <th>PRICE (NESO)</th>
                        <th>EST. FAIR</th>
                        <th>VS FLOOR</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {view === "underpriced" ? enriched.map((char: any) => {
                    const vsFair =
                      char.fair_value > 0 && char.price > 0
                        ? ((char.price - char.fair_value) / char.fair_value) * 100
                        : null;
                    return (
                      <tr
                        key={char.token_id}
                        className={`cursor-pointer transition-colors ${selectedTokenId === char.token_id
                          ? "bg-terminal-accent/5 border-l-2 border-l-terminal-accent"
                          : ""
                        }`}
                        onClick={() => setSelectedTokenId(char.token_id)}
                      >
                        <td className="text-terminal-text font-medium max-w-[180px] truncate">
                          {char.asset_key ? (
                            <a
                              href={`https://msu.io/navigator/character/${char.asset_key}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:underline hover:text-terminal-accent"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {char.name}
                            </a>
                          ) : char.name}
                        </td>
                        <td>
                          <span className={`text-[10px] font-mono font-black tracking-tighter px-1.5 py-0.5 rounded ${CLASS_BG[char.class_name] || "bg-white/5"} ${CLASS_COLORS[char.class_name] || "text-white"}`}>
                            {char.class_name?.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <span className={`font-mono text-xs ${char.level >= 240 ? "text-terminal-red font-black" : char.level >= 200 ? "text-terminal-yellow font-bold" : "text-terminal-text"}`}>
                            LV.{char.level}
                          </span>
                        </td>
                        <td>{char.arcane_set_tier ? arcaneBadge(char.arcane_set_tier) : <span className="text-terminal-muted/50">—</span>}</td>
                        <td className={abilityColor(char.ability_total)}>
                          <span className="font-mono text-xs">{char.ability_total}</span>
                        </td>
                        <td className="text-terminal-accent font-bold tabular-nums">
                          {char.price?.toLocaleString()}
                        </td>
                        <td>
                          {char.fair_value > 0 ? (
                            <span className="text-terminal-cyan font-mono text-xs tabular-nums">
                              {char.fair_value.toLocaleString()}
                            </span>
                          ) : (
                            <span className="text-terminal-yellow font-mono text-xs">
                              <span className="inline-block w-2.5 h-2.5 border-2 border-terminal-yellow/40 border-t-transparent rounded-full animate-spin mr-1 align-middle" />
                              ENRICHING
                            </span>
                          )}
                        </td>
                        <td>
                          {vsFair !== null ? (
                            <span
                              className={`text-[11px] font-mono font-bold ${vsFair <= -15 ? "text-terminal-green scale-110" : vsFair < 0 ? "text-terminal-green" : vsFair > 40 ? "text-terminal-red opacity-50" : "text-terminal-muted"}`}
                            >
                              {vsFair > 0 ? "+" : ""}{vsFair.toFixed(0)}%
                            </span>
                          ) : <span className="text-terminal-yellow font-mono text-xs">WAITING</span>}
                        </td>
                        <td className="text-terminal-text text-xs font-mono">
                          {char.gear_score?.toFixed(0)}
                        </td>
                      </tr>
                    );
                  })
                  :
                  chars.map((char: any) => {
                    let closestBracket = "0";
                    for (const th of floorData?.thresholds || FLOOR_LEVELS) {
                      if (char.level >= th) closestBracket = String(th);
                      else break;
                    }
                    const floorEntry = floors[char.class_name]?.[closestBracket];
                    const floorPrice = floorEntry?.min_price;
                    const vsFloor =
                      floorPrice && char.price > 0
                        ? ((char.price - floorPrice) / floorPrice) * 100
                        : null;
                    return (
                      <tr
                        key={char.token_id}
                        className={`cursor-pointer transition-colors ${selectedTokenId === char.token_id
                          ? "bg-terminal-accent/5 border-l-2 border-l-terminal-accent"
                          : ""
                        }`}
                        onClick={() => setSelectedTokenId(char.token_id)}
                      >
                        <td className="text-terminal-text font-medium max-w-[200px] truncate">
                          {char.asset_key ? (
                            <a
                              href={`https://msu.io/navigator/character/${char.asset_key}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:underline hover:text-terminal-accent"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {char.name}
                            </a>
                          ) : char.name}
                        </td>
                        <td>
                          <span className={`text-[10px] font-mono font-black tracking-tighter px-1.5 py-0.5 rounded ${CLASS_BG[char.class_name] || "bg-white/5"} ${CLASS_COLORS[char.class_name] || "text-terminal-text"}`}>
                            {char.class_name?.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <span className={`font-mono text-xs ${char.level >= 240 ? "text-terminal-red font-black" : char.level >= 200 ? "text-terminal-yellow font-bold" : "text-terminal-text"}`}>
                            LV.{char.level}
                          </span>
                        </td>
                        <td className="text-terminal-accent font-bold tabular-nums">
                          {char.price?.toLocaleString()}
                        </td>
                        <td>
                          {char.fair_value_estimate > 0 ? (
                            <span className="text-terminal-cyan font-mono text-xs tabular-nums">
                              {char.fair_value_estimate.toLocaleString()}
                            </span>
                          ) : (
                            <span className="text-terminal-muted font-mono text-xs">—</span>
                          )}
                        </td>
                        <td>
                          {vsFloor !== null ? (
                            <span
                              className={`text-[11px] font-mono font-bold ${vsFloor <= -15 ? "text-terminal-green scale-110" : vsFloor < 0 ? "text-terminal-green" : vsFloor > 40 ? "text-terminal-red opacity-50" : "text-terminal-muted"}`}
                            >
                              {vsFloor > 0 ? "+" : ""}{vsFloor.toFixed(0)}%
                            </span>
                          ) : <span className="text-terminal-muted/20">---</span>}
                        </td>
                      </tr>
                    );
                  })
                  }
                </tbody>
              </table>
            )}
          </div>
          <div className="px-4 py-3 border-t border-terminal-border flex items-center justify-between bg-black/20">
            <button
              onClick={() => { setPage((p) => Math.max(1, p - 1)); window.scrollTo(0, 0); }}
              disabled={page === 1}
              className="px-4 py-1 text-[10px] font-mono text-terminal-muted hover:text-terminal-accent border border-terminal-border rounded disabled:opacity-10"
            >
              PREVIOUS_BLOCK
            </button>
            <span className="text-[10px] font-mono text-terminal-muted tracking-[0.3em]">
              PROTOCOL_PAGE_0{page}
            </span>
            <button
              onClick={() => { setPage((p) => p + 1); window.scrollTo(0, 0); }}
              disabled={view === "explore" && data?.is_last_page}
              className="px-4 py-1 text-[10px] font-mono text-terminal-muted hover:text-terminal-accent border border-terminal-border rounded disabled:opacity-10"
            >
              NEXT_BLOCK
            </button>
          </div>
          {view === "underpriced" && enrichedTotal > enriched.length && enriched.length > 0 && (
            <div className="px-4 py-2 border-t border-terminal-yellow/20 bg-terminal-yellow/5 flex items-center gap-2">
              <span className="inline-block w-3 h-3 border-2 border-terminal-yellow/50 border-t-transparent rounded-full animate-spin" />
              <span className="text-[10px] font-mono text-terminal-yellow">
                Enriching {enriched.length} of {enrichedTotal} — results update as data becomes available
              </span>
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="space-y-6">
          {detail && (
            <div className="panel border-terminal-accent/30 shadow-[0_0_20px_rgba(var(--terminal-accent),0.1)]">
              <div className="panel-header bg-terminal-accent/5">
                <span className="panel-title text-terminal-accent">SUBJECT ANALYSIS</span>
              </div>
              <div className="p-5 space-y-5">
                <div className="flex gap-4 items-start">
                  <div className="w-16 h-16 bg-black/40 border border-white/5 rounded-lg flex items-center justify-center p-1">
                    <img src={detail.image_url || "/char_placeholder.png"} className="w-full h-full object-contain filter drop-shadow-lg" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-base font-mono font-bold text-terminal-text">{detail.name}</h3>
                    <p className={`text-[11px] font-mono ${CLASS_COLORS[detail.class_name] || ""}`}>
                      {detail.class_name} // {detail.job_name}
                    </p>
                    <div className="mt-2 text-xl font-mono font-black text-terminal-accent">{detail.price?.toLocaleString()} <span className="text-[10px]">NESO</span></div>
                  </div>
                </div>

                {detail.ap_stats && (
                  <div className="bg-black/20 rounded p-3 border border-white/5">
                    <p className="text-[9px] font-mono text-white/20 uppercase mb-2 tracking-[0.2em]">Matrix AP Protocol</p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                      {[["STR", detail.ap_stats.str_stat?.total], ["DEX", detail.ap_stats.dex?.total], ["INT", detail.ap_stats.int_stat?.total], ["LUK", detail.ap_stats.luk?.total], ["DMG", detail.ap_stats.damage?.total], ["BOSS", detail.ap_stats.boss_monster_damage?.total], ["IED", detail.ap_stats.ignore_defence?.total]]
                        .filter(([, v]) => v && v > 0)
                        .map(([label, val]) => (
                          <div key={label as string} className="flex justify-between text-[10px] font-mono">
                            <span className="text-terminal-muted">{label}</span>
                            <span className="text-terminal-text">{(val as number)?.toLocaleString()}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Floor prices updated with threshold logic */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">MARKET FLOOR TIERS</span>
              <span className="text-[10px] font-mono text-terminal-muted">INDEX: {floorData?.sample_size || 0}</span>
            </div>
            <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
              {Object.entries(floors).sort((a, b) => a[0].localeCompare(b[0])).map(
                ([cls, brackets]: [string, any]) => (
                  <div key={cls} className="px-4 py-4 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
                    <div className="flex justify-between items-center mb-2">
                      <p className={`text-xs font-mono font-black ${CLASS_COLORS[cls] || "text-terminal-text"}`}>{cls.toUpperCase()}</p>
                      <span className="text-[10px] text-white/10 font-mono">LVL_BASKETS</span>
                    </div>
                    <div className="flex gap-8">
                      <div className="flex-1 space-y-1">
                        {FLOOR_LEVELS.slice(0, 4).map(lvl => {
                          const info = brackets[String(lvl)];
                          if (!info) return null;
                          return (
                            <div key={lvl} className="flex justify-between text-[11px] font-mono border-b border-white/[0.03] pb-0.5">
                              <span className="text-terminal-muted">LV.{lvl}</span>
                              <span className="text-terminal-text font-bold">
                                {info.min_price?.toLocaleString()}
                                <span className="text-[9px] text-terminal-muted ml-1 opacity-40">
                                  ({info.sample_size || info.count})
                                  {info.median_price && ` // Med: ${info.median_price?.toLocaleString()}`}
                                </span>
                              </span>
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex-1 space-y-1">
                        {FLOOR_LEVELS.slice(4).map(lvl => {
                          const info = brackets[String(lvl)];
                          if (!info) return null;
                          return (
                            <div key={lvl} className="flex justify-between text-[11px] font-mono border-b border-white/[0.03] pb-0.5">
                              <span className="text-terminal-muted">LV.{lvl}</span>
                              <span className="text-terminal-text font-bold">
                                {info.min_price?.toLocaleString()}
                                <span className="text-[9px] text-terminal-muted ml-1 opacity-40">
                                  ({info.sample_size || info.count})
                                  {info.median_price && ` // Med: ${info.median_price?.toLocaleString()}`}
                                </span>
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
