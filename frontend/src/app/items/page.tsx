"use client";

import { useState, useMemo } from "react";
import {
  useItems,
  useItemOHLC,
  useScarcityRanking,
  useTradeHistory,
  useItemFloorPrices,
  useUnderpricedItems,
} from "@/hooks/useMarketData";
import OHLCChart from "@/components/OHLCChart";
import ScarcityBadge from "@/components/ScarcityBadge";

const POTENTIAL_LABELS: Record<number, [string, string]> = {
  0: ["NORMAL", "text-terminal-muted"],
  1: ["RARE", "badge-cyan"],
  2: ["EPIC", "badge-purple"],
  3: ["UNIQUE", "badge-yellow"],
  4: ["LEGENDARY", "badge-green"],
  5: ["SPECIAL", "badge-red"],
  6: ["MYTHIC", "badge-red"],
};

function PotentialBadge({ grade }: { grade: number }) {
  const [label, cls] = POTENTIAL_LABELS[grade] || ["?", "text-terminal-muted"];
  if (grade === 0)
    return <span className="text-terminal-muted text-xs">-</span>;
  return <span className={cls}>{label}</span>;
}

export default function ItemsPage() {
  const [page, setPage] = useState(1);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [selectedItemName, setSelectedItemName] = useState<string>("");
  const [sorting, setSorting] = useState("ExploreSorting_RECENTLY_LISTED");
  const [interval, setInterval] = useState(60);

  const { data, isLoading } = useItems(page, 50, sorting);
  const { data: ohlcData } = useItemOHLC(selectedItemId, interval);
  const { data: ranking } = useScarcityRanking(30);
  const { data: tradeData } = useTradeHistory(selectedItemId);
  const { data: itemFloorData } = useItemFloorPrices();
  const { data: underpricedData } = useUnderpricedItems(0.15, 500);

  const items = data?.items || [];
  const itemFloors = itemFloorData?.floor_prices || {};

  // Fair value lookup computed via memo: name -> sf -> pot -> bpot -> {floor, median}
  const fairLookup = useMemo(() => {
    const fl: Record<string, any> = {};
    for (const [name, sfMap] of Object.entries(itemFloors)) {
      if (typeof sfMap !== "object" || sfMap === null) continue;
      fl[name] = {};
      for (const [sf, gradeMap] of Object.entries(sfMap as Record<string, unknown>)) {
        if (typeof gradeMap !== "object" || gradeMap === null) continue;
        fl[name][sf] = {};
        for (const [pot, bpotMap] of Object.entries(gradeMap as Record<string, unknown>)) {
          if (typeof bpotMap !== "object" || bpotMap === null) continue;
          fl[name][sf][pot] = {};
          for (const [bpot, info] of Object.entries(bpotMap as Record<string, unknown>)) {
            const d = info as Record<string, number>;
            if (d?.median) {
              fl[name][sf][pot][bpot] = { floor: d.floor || 0, median: d.median };
            }
          }
        }
      }
    }
    return fl;
  }, [itemFloors]);

  function getFairValue(item: { name: string; starforce: number; potential_grade: number; bonus_potential_grade: number; price?: number }): { fair: number; discount: number; asset_key?: string } {
    const name = item.name;
    const sfKey = item.starforce > 0 ? `SF${item.starforce}` : "NSF";
    const potKey = String(item.potential_grade);
    const bpotKey = String(item.bonus_potential_grade || 0);

    const nameMap: any = (fairLookup as any)?.[name];
    const sfMap: any = nameMap?.[sfKey];
    const potMap: any = sfMap?.[potKey];
    const bpotInfo: any = potMap?.[bpotKey];
    let median = bpotInfo?.median as number | undefined;

    // Fallback: any bonus potential tier for this pot + sf
    if (!median && potMap && typeof potMap === "object") {
      const entries = Object.values(potMap as Record<string, any>);
      for (const e of entries) {
        if (e?.median) { median = e.median; break; }
      }
    }

    // Fallback: any potential tier for this sf
    if (!median && sfMap && typeof sfMap === "object") {
      const potEntries = Object.values(sfMap as Record<string, any>);
      for (const p of potEntries) {
        if (p && typeof p === "object") {
          for (const e of Object.values(p as Record<string, any>)) {
            if ((e as any)?.median) { median = (e as any).median; break; }
          }
        }
        if (median) break;
      }
    }

    if (!median) return { fair: 0, discount: 0 };
    const price = item.price || 0;
    if (price <= 0) return { fair: median, discount: 0 };
    return { fair: median, discount: ((median - price) / median) * 100 };
  }

  function getItemAssetKey(item: any): string | undefined {
    return item.asset_key || item.token_id;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
            ITEM EXPLORER
          </h2>
          <p className="text-xs font-mono text-terminal-muted mt-1">
            Browse, analyze, and track item prices across the marketplace
          </p>
        </div>
        <div className="flex gap-2">
          {[
            ["ExploreSorting_RECENTLY_LISTED", "RECENT"],
            ["ExploreSorting_PRICE_LOW_TO_HIGH", "PRICE ASC"],
            ["ExploreSorting_PRICE_HIGH_TO_LOW", "PRICE DESC"],
          ].map(([val, label]) => (
            <button
              key={val}
              onClick={() => {
                setSorting(val);
                setPage(1);
              }}
              className={`px-2 py-1 text-[10px] font-mono rounded border transition-all ${
                sorting === val
                  ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                  : "border-terminal-border text-terminal-muted hover:text-terminal-text"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* OHLC Chart */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">
            PRICE CHART{selectedItemName ? ` - ${selectedItemName}` : ""}
            {selectedItemId ? ` (ID: ${selectedItemId})` : ""}
          </span>
          <div className="flex gap-2">
            {[
              [15, "15M"],
              [60, "1H"],
              [240, "4H"],
              [1440, "1D"],
            ].map(([mins, label]) => (
              <button
                key={label as string}
                onClick={() => setInterval(mins as number)}
                className={`px-2 py-1 text-[10px] font-mono border rounded transition-all ${
                  interval === mins
                    ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                    : "border-terminal-border text-terminal-muted hover:text-terminal-accent"
                }`}
              >
                {label as string}
              </button>
            ))}
          </div>
        </div>
        <div className="p-4">
          {selectedItemId && ohlcData?.bars?.length ? (
            <OHLCChart data={ohlcData.bars} />
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-terminal-muted font-mono text-sm gap-2">
              {selectedItemId ? (
                tradeData?.count === 0 ? (
                  "No trade history available for this item"
                ) : (
                  "Loading chart data..."
                )
              ) : (
                <>
                  <span>Select an item from the table to view price chart</span>
                  <span className="text-[10px]">
                    Click any row below to load OHLC data from trade history
                  </span>
                </>
              )}
            </div>
          )}
          {tradeData?.count > 0 && (
            <div className="mt-2 text-[10px] font-mono text-terminal-muted text-right">
              {tradeData.count} trades loaded
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Items table */}
        <div className="xl:col-span-2 panel">
          <div className="panel-header">
            <span className="panel-title">MARKETPLACE LISTINGS</span>
            <span className="text-[10px] font-mono text-terminal-muted">
              {data?.count || 0} items | Page {page}
              {data?.is_last_page && " (last)"}
            </span>
          </div>
          <div className="max-h-[600px] overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm">
                Fetching items from MSU API...
              </div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm">
                No items found
              </div>
            ) : (
              <table className="data-table">
                <thead className="sticky top-0 bg-terminal-panel z-10">
                  <tr>
                    <th>NAME</th>
                    <th>CATEGORY</th>
                    <th>SF</th>
                    <th>POTENTIAL</th>
                    <th>PRICE (NESO)</th>
                    <th>FAIR VALUE</th>
                    <th>DISCOUNT</th>
                    <th>LISTED</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item: any) => {
                    const { fair, discount } = getFairValue(item);
                    const assetKey = getItemAssetKey(item);
                    return (
                      <tr
                        key={item.token_id}
                        className={`cursor-pointer transition-colors ${
                          selectedItemId === item.item_id
                            ? "bg-terminal-accent/5 border-l-2 border-terminal-accent"
                            : ""
                        }`}
                        onClick={() => {
                          setSelectedItemId(item.item_id);
                          setSelectedItemName(item.name);
                        }}
                      >
                        <td className="text-terminal-text font-medium max-w-[200px] truncate">
                          {assetKey ? (
                            <a
                              href={`https://msu.io/navigator/item/${assetKey}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:underline hover:text-terminal-accent"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {item.name}
                            </a>
                          ) : (
                            item.name
                          )}
                        </td>
                        <td className="text-terminal-muted text-[10px] max-w-[120px] truncate">
                          {item.category_label
                            ? item.category_label.split(" > ").slice(-1)[0]
                            : "-"}
                        </td>
                        <td>
                          <span
                            className={`font-mono ${
                              item.starforce >= 20
                                ? "text-terminal-red font-bold"
                                : item.starforce >= 15
                                ? "text-terminal-yellow font-bold"
                                : item.starforce > 0
                                ? "text-terminal-text"
                                : "text-terminal-muted"
                            }`}
                          >
                            {item.starforce > 0 ? `+${item.starforce}` : "-"}
                          </span>
                        </td>
                        <td>
                          <PotentialBadge grade={item.potential_grade} />
                        </td>
                        <td className="text-terminal-accent font-medium tabular-nums">
                          {item.price?.toLocaleString() || "---"}
                        </td>
                        <td>
                          {fair > 0 ? (
                            <span className="text-terminal-cyan font-mono text-xs tabular-nums">
                              {fair.toLocaleString()}
                            </span>
                          ) : (
                            <span className="text-terminal-muted font-mono text-xs">-</span>
                          )}
                        </td>
                        <td>
                          {fair > 0 && item.price > 0 ? (
                            <span
                              className={`text-[10px] font-mono font-bold ${
                                discount > 20
                                  ? "text-terminal-green scale-110"
                                  : discount > 0
                                  ? "text-terminal-green"
                                  : discount < -20
                                  ? "text-terminal-red"
                                  : "text-terminal-muted"
                              }`}
                            >
                              {discount > 0 ? `+${discount.toFixed(0)}%` : `${discount.toFixed(0)}%`}
                            </span>
                          ) : (
                            <span className="text-terminal-muted font-mono text-xs">-</span>
                          )}
                        </td>
                        <td className="text-terminal-muted text-[10px]">
                          {item.created_at
                            ? new Date(item.created_at).toLocaleDateString()
                            : "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <div className="px-4 py-3 border-t border-terminal-border flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="text-xs font-mono text-terminal-muted hover:text-terminal-accent disabled:opacity-30"
            >
              PREV
            </button>
            <span className="text-xs font-mono text-terminal-muted">
              PAGE {page}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={data?.is_last_page}
              className="text-xs font-mono text-terminal-muted hover:text-terminal-accent disabled:opacity-30"
            >
              NEXT
            </button>
          </div>
        </div>

        {/* Scarcity Ranking */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">SCARCITY RANKING</span>
            <span className="text-[10px] font-mono text-terminal-muted">
              Top {ranking?.ranking?.length || 0}
            </span>
          </div>
          <div className="max-h-[600px] overflow-y-auto">
            {ranking?.ranking?.length ? (
              <div className="divide-y divide-terminal-border/50">
                {ranking.ranking.map((item: any, i: number) => (
                  <div
                    key={item.token_id}
                    className="px-4 py-3 flex items-center justify-between hover:bg-terminal-surface/50 cursor-pointer"
                    onClick={() => {
                      if (item.item_id) {
                        setSelectedItemId(item.item_id);
                        setSelectedItemName(item.name);
                      }
                    }}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span
                        className={`text-xs font-mono w-6 flex-shrink-0 ${
                          i < 3 ? "text-terminal-yellow font-bold" : "text-terminal-muted"
                        }`}
                      >
                        #{i + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-mono text-terminal-text truncate">
                          {item.name}
                        </p>
                        <p className="text-[10px] font-mono text-terminal-muted">
                          {item.starforce > 0 && `SF${item.starforce} `}
                          {item.potential_grade > 0 &&
                            POTENTIAL_LABELS[item.potential_grade]?.[0]}{" "}
                          | Fair: {item.fair_value_estimate?.toLocaleString()} NESO
                        </p>
                      </div>
                    </div>
                    <ScarcityBadge score={item.score} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm">
                Computing scarcity rankings...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Item Floor Prices */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">ITEM FLOOR PRICES</span>
          <span className="text-[10px] font-mono text-terminal-muted">
            INDEX: {itemFloorData?.sample_size || 0} items
          </span>
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          {Object.entries(itemFloors).length === 0 ? (
            <div className="p-6 text-center text-terminal-muted text-xs font-mono">Loading floor data...</div>
          ) : (
            (() => {
              // Flatten 4-level nested structure: name -> sf_bracket -> pot_grade -> bpot_grade -> {floor, median, count}
              const flat: { name: string; sf: string; pot: string; bpot: string; floor: number; median: number; count: number }[] = [];
              for (const [name, sfMap] of Object.entries(itemFloors)) {
                if (typeof sfMap !== "object" || sfMap === null) continue;
                for (const [sf, gradeMap] of Object.entries(sfMap as Record<string, unknown>)) {
                  if (typeof gradeMap !== "object" || gradeMap === null) continue;
                  for (const [pot, bpotMap] of Object.entries(gradeMap as Record<string, unknown>)) {
                    if (typeof bpotMap !== "object" || bpotMap === null) continue;
                    for (const [bpot, info] of Object.entries(bpotMap as Record<string, unknown>)) {
                      const d = info as Record<string, number>;
                      if (d?.floor) {
                        const potLabel = ["None", "Rare", "Epic", "Unique", "Legendary", "Special", "Mythic"][Number(pot)] || pot;
                        const bpotLabel = ["-", "Rare", "Epic", "Unique", "Legendary", "Special", "Mythic"][Number(bpot)] || bpot;
                        flat.push({ name, sf, pot: potLabel, bpot: bpotLabel, floor: d.floor, median: d.median || 0, count: d.count || 0 });
                      }
                    }
                  }
                }
              }
              return (
                <table className="data-table">
                  <thead className="sticky top-0 bg-terminal-panel z-10">
                    <tr>
                      <th>ITEM</th>
                      <th>SF</th>
                      <th>POT</th>
                      <th>BPOT</th>
                      <th>FLOOR</th>
                      <th>MEDIAN</th>
                      <th>COUNT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flat.sort((a, b) => b.floor - a.floor).slice(0, 80).map((r, i) => (
                      <tr key={i}>
                        <td className="text-terminal-text text-xs truncate max-w-[200px]">{r.name}</td>
                        <td className="text-terminal-yellow text-xs">{r.sf}</td>
                        <td className="text-[10px]">{r.pot}</td>
                        <td className="text-[10px]">{r.bpot}</td>
                        <td className="text-terminal-green font-bold">{r.floor.toLocaleString()}</td>
                        <td className="text-terminal-cyan">{r.median.toLocaleString()}</td>
                        <td className="text-terminal-muted text-[10px]">{r.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              );
            })()
          )}
        </div>
      </div>
    </div>
  );
}
