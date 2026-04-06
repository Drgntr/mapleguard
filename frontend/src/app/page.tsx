"use client";

import {
  useMarketOverview,
  useRecentlyListed,
  useUnderpricedItems,
} from "@/hooks/useMarketData";
import UnderpricedTable from "@/components/UnderpricedTable";
import AnomalyAlert from "@/components/AnomalyAlert";

function StatCard({
  label,
  value,
  sub,
  color = "text-terminal-text",
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="panel p-4">
      <p className="stat-label mb-1">{label}</p>
      <p className={`stat-value ${color}`}>{value}</p>
      {sub && <p className="text-[10px] font-mono text-terminal-muted mt-1">{sub}</p>}
    </div>
  );
}

function DistributionBar({
  data,
  colorMap,
}: {
  data: Record<string, number>;
  colorMap?: Record<string, string>;
}) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  const defaultColors: Record<string, string> = {
    Archer: "bg-terminal-green",
    Magician: "bg-terminal-purple",
    Pirate: "bg-terminal-cyan",
    Thief: "bg-terminal-red",
    Warrior: "bg-terminal-yellow",
    None: "bg-terminal-muted",
    Rare: "bg-terminal-cyan",
    Epic: "bg-terminal-purple",
    Unique: "bg-terminal-yellow",
    Legendary: "bg-terminal-green",
    Special: "bg-terminal-red",
    Mythic: "bg-terminal-accent",
  };
  const colors = colorMap || defaultColors;

  return (
    <div>
      <div className="flex h-3 rounded overflow-hidden gap-0.5">
        {Object.entries(data).map(([key, val]) => (
          <div
            key={key}
            className={`${colors[key] || "bg-terminal-border"} transition-all`}
            style={{ width: `${(val / total) * 100}%` }}
            title={`${key}: ${val}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {Object.entries(data).map(([key, val]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-sm ${colors[key] || "bg-terminal-border"}`} />
            <span className="text-[10px] font-mono text-terminal-muted">
              {key}: {val} ({((val / total) * 100).toFixed(0)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function OverviewPage() {
  const { data: overview, isLoading } = useMarketOverview();
  const { data: recentData } = useRecentlyListed(20);
  const { data: underpriced } = useUnderpricedItems(0.25);

  const o = overview || {};

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
          MARKET OVERVIEW
        </h2>
        <p className="text-xs font-mono text-terminal-muted mt-1">
          MapleStory Universe marketplace real-time intelligence
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
        <StatCard
          label="LISTED ITEMS"
          value={isLoading ? "---" : (o.total_listed_items || 0).toLocaleString()}
        />
        <StatCard
          label="LISTED CHARACTERS"
          value={isLoading ? "---" : (o.total_listed_characters || 0).toLocaleString()}
        />
        <StatCard
          label="AVG ITEM PRICE"
          value={isLoading ? "---" : `${(o.avg_item_price || 0).toLocaleString()}`}
          sub={`Median: ${(o.median_item_price || 0).toLocaleString()} NESO`}
          color="text-terminal-cyan"
        />
        <StatCard
          label="AVG CHAR PRICE"
          value={isLoading ? "---" : `${(o.avg_character_price || 0).toLocaleString()}`}
          sub={`Median: ${(o.median_character_price || 0).toLocaleString()} NESO`}
          color="text-terminal-purple"
        />
        <StatCard
          label="CONSUMABLES"
          value={isLoading ? "---" : (o.total_consumables || 0).toString()}
          color="text-terminal-yellow"
        />
        <StatCard
          label="SNIPER"
          value={isLoading ? "---" : (o.sniper_activity?.total_snipes || 0).toString()}
          sub={o.sniper_activity?.running ? "SCANNING" : "IDLE"}
          color={(o.sniper_activity?.total_snipes || 0) > 0 ? "text-terminal-red" : "text-terminal-muted"}
        />
        <StatCard
          label="ANOMALIES"
          value={isLoading ? "---" : (o.anomaly_stats?.total_alerts || 0).toString()}
          color={
            (o.anomaly_stats?.total_alerts || 0) > 0
              ? "text-terminal-red"
              : "text-terminal-green"
          }
        />
      </div>

      {/* Distribution panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {o.class_distribution && (
          <div className="panel p-4">
            <p className="panel-title mb-3">CLASS DISTRIBUTION</p>
            <DistributionBar data={o.class_distribution} />
          </div>
        )}
        {o.potential_distribution && (
          <div className="panel p-4">
            <p className="panel-title mb-3">POTENTIAL DISTRIBUTION</p>
            <DistributionBar data={o.potential_distribution} />
          </div>
        )}
      </div>

      {/* Top consumables */}
      {o.top_consumables?.length > 0 && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">TOP CONSUMABLES</span>
            <span className="badge-yellow">VOLUME</span>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>NAME</th>
                  <th>PRICE (NESO)</th>
                  <th>VOLUME</th>
                  <th>CHANGE</th>
                </tr>
              </thead>
              <tbody>
                {o.top_consumables.map((c: any, i: number) => (
                  <tr key={i}>
                    <td className="text-terminal-text">{c.name}</td>
                    <td className="text-terminal-accent">
                      {c.price?.toLocaleString() || "---"}
                    </td>
                    <td className="text-terminal-cyan">{c.volume?.toLocaleString()}</td>
                    <td>
                      <span
                        className={
                          c.change > 0
                            ? "text-terminal-green"
                            : c.change < 0
                            ? "text-terminal-red"
                            : "text-terminal-muted"
                        }
                      >
                        {c.change > 0 ? "+" : ""}
                        {c.change?.toFixed(2)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Two column layout */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Recently Listed Feed */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">RECENTLY LISTED</span>
            <span className="text-[10px] font-mono text-terminal-green animate-pulse-slow">
              LIVE
            </span>
          </div>
          <div className="max-h-[500px] overflow-y-auto">
            {recentData?.listed?.length ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>NAME</th>
                    <th>TYPE</th>
                    <th>DETAIL</th>
                    <th>PRICE (NESO)</th>
                    <th>TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {recentData.listed.map((item: any, i: number) => (
                    <tr key={i}>
                      <td className="text-terminal-text font-medium">
                        {item.name || `#${item.token_id?.slice(0, 8)}`}
                      </td>
                      <td>
                        <span
                          className={
                            item.token_type === "characters"
                              ? "badge-purple"
                              : "badge-cyan"
                          }
                        >
                          {item.token_type === "characters" ? "CHAR" : "ITEM"}
                        </span>
                      </td>
                      <td className="text-terminal-muted text-xs">
                        {item.token_type === "characters" ? (
                          <span>
                            {item.class_name} Lv.{item.level}
                          </span>
                        ) : (
                          <span>
                            {item.starforce > 0 && `SF${item.starforce} `}
                            {item.potential_grade > 0 &&
                              ["", "R", "E", "U", "L", "S", "M"][
                                item.potential_grade
                              ] + " Pot"}
                          </span>
                        )}
                      </td>
                      <td className="text-terminal-accent font-medium">
                        {item.price?.toLocaleString() || "---"}
                      </td>
                      <td className="text-terminal-muted text-[10px]">
                        {item.created_at
                          ? new Date(item.created_at).toLocaleTimeString()
                          : "---"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-terminal-muted text-sm font-mono">
                Loading feed...
              </div>
            )}
          </div>
        </div>

        {/* Underpriced Items */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">UNDERPRICED ITEMS</span>
            <span className="badge-green">OPPORTUNITIES</span>
          </div>
          <div className="max-h-[500px] overflow-y-auto">
            <UnderpricedTable items={underpriced?.items || []} />
          </div>
        </div>
      </div>

      {/* Anomaly section */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">SENTINEL ALERTS</span>
          <span className="badge-red">ANOMALY DETECTION</span>
        </div>
        <AnomalyAlert />
      </div>
    </div>
  );
}
