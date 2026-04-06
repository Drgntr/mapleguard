"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useJobsList, useJobLeaderboard, type JobInfo } from "@/hooks/useMarketData";

interface LeaderboardEntry {
  token_id: string;
  name: string;
  class_name: string;
  job_name?: string;
  level: number;
  price: number;
  cp: number;
  combat_power?: number;
  image_url: string;
}

const CLASS_COLORS: Record<string, string> = {
  Warrior: "text-terminal-red",
  Magician: "text-terminal-purple",
  Bowman: "text-terminal-green",
  Thief: "text-terminal-yellow",
  Pirate: "text-terminal-cyan",
};

const CLASS_BADGE: Record<string, string> = {
  Warrior: "bg-terminal-red/10 text-terminal-red border-terminal-red/30",
  Magician: "bg-terminal-purple/10 text-terminal-purple border-terminal-purple/30",
  Bowman: "bg-terminal-green/10 text-terminal-green border-terminal-green/30",
  Thief: "bg-terminal-yellow/10 text-terminal-yellow border-terminal-yellow/30",
  Pirate: "bg-terminal-cyan/10 text-terminal-cyan border-terminal-cyan/30",
};

function getClassType(className: string): string {
  const lower = className.toLowerCase();
  if (["hero", "dark knight", "paladin", "mihile", "aran", "kaiser", "blaster", "demon slayer", "demon avenger", "hayato", "zero", "adele", "dawn warrior"].some(n => lower.includes(n))) return "Warrior";
  if (["bishop", "fire poison", "ice lightning", "fire/poison", "ice/lightning", "luminous", "phantom", "eva", "kinesis", "illium", "khali", "battl mage", "blaze wizard", "kanna"].some(n => lower.includes(n))) return "Magician";
  if (["bowmaster", "marksman", "pathfinder", "wind archer", "mercedes", "wild hunter", "angeli buster", "kain"].some(n => lower.includes(n))) return "Bowman";
  if (["shadower", "night lord", "dual blade", "night walker", "shade", "cadena", "hoyoung"].some(n => lower.includes(n))) return "Thief";
  if (["buccaneer", "corsair", "cannoneer", "thunder breaker", "xenon", "mekanic"].some(n => lower.includes(n))) return "Pirate";
  return "";
}

export default function LeaderboardsPage() {
  const [activeTab, setActiveTab] = useState<"class" | "job">("class");
  const [activeClass, setActiveClass] = useState<string>("all");
  const [activeJob, setActiveJob] = useState<string | null>(null);

  // Class leaderboard (old)
  const { data: classData, isLoading: classLoading } = useQuery<{
    characters: LeaderboardEntry[];
    classes: Record<string, LeaderboardEntry[]>;
    total_scored: number;
  }>({
    queryKey: ["leaderboard-scan"],
    queryFn: async () => {
      const res = await fetch("/api/leaderboard/scan?limit=100");
      return res.json();
    },
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
    enabled: activeTab === "class",
  });

  // Job leaderboard (new)
  const { data: jobs, isLoading: jobsLoading } = useJobsList();
  const { data: jobData, isLoading: jobLoading } = useJobLeaderboard(
    activeTab === "job" ? (activeJob ?? undefined) : undefined,
    100
  );

  // Class data
  const allChars = classData?.characters || [];
  const classGroups = classData?.classes || {};
  const availableClasses = allChars.length > 0
    ? Object.keys(classGroups).sort((a, b) => (classGroups[b]?.length || 0) - (classGroups[a]?.length || 0))
    : [];

  // Job display data
  const jobTop10 = jobData?.top10 || [];
  const jobAll = jobData?.all || [];
  const jobTotal = jobData?.total || 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
          CP LEADERBOARD
        </h2>
        <p className="text-xs font-mono text-terminal-muted mt-1">
          Character Combat Power rankings — real CP from MSU Open API
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => { setActiveTab("class"); setActiveJob(null); }}
          className={`px-4 py-1.5 text-[10px] font-mono rounded border transition-all ${
            activeTab === "class"
              ? "bg-terminal-accent/10 text-terminal-accent border-terminal-accent/40"
              : "text-terminal-muted border-terminal-border hover:text-terminal-text"
          }`}
        >
          BY CLASS
        </button>
        <button
          onClick={() => { setActiveTab("job"); setActiveClass("all"); }}
          className={`px-4 py-1.5 text-[10px] font-mono rounded border transition-all ${
            activeTab === "job"
              ? "bg-terminal-accent/10 text-terminal-accent border-terminal-accent/40"
              : "text-terminal-muted border-terminal-border hover:text-terminal-text"
          }`}
        >
          BY JOB
        </button>
      </div>

      {/* ===== CLASS VIEW ===== */}
      {activeTab === "class" && (
        <>
          {/* Class filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveClass("all")}
              className={`px-3 py-1.5 text-[10px] font-mono rounded border transition-all ${
                activeClass === "all"
                  ? "bg-terminal-accent/10 text-terminal-accent border-terminal-accent/40"
                  : "text-terminal-muted border-terminal-border hover:text-terminal-text"
              }`}
            >
              ALL
            </button>
            {availableClasses.map(cls => {
              const classType = getClassType(cls);
              const badge = CLASS_BADGE[classType] || "bg-terminal-panel text-terminal-text border-terminal-border";
              return (
                <button
                  key={cls}
                  onClick={() => setActiveClass(cls)}
                  className={`px-3 py-1.5 text-[10px] font-mono rounded border transition-all ${
                    activeClass === cls
                      ? `${badge} border-opacity-60`
                      : "text-terminal-muted border-terminal-border hover:text-terminal-text"
                  }`}
                >
                  {cls} ({classGroups[cls]?.length || 0})
                </button>
              );
            })}
          </div>

          {/* Class podium */}
          {(() => {
            const displayChars = activeClass === "all" ? allChars : (classGroups[activeClass] || []);
            if (displayChars.length < 3) return null;
            return (
              <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
                {[1, 0, 2].map((idx, renderIdx) => {
                  const char = displayChars[idx];
                  if (!char) return null;
                  const classType = getClassType(char.class_name);
                  const color = CLASS_COLORS[classType] || "text-terminal-text";
                  const medalColor = idx === 0 ? "text-terminal-yellow" : idx === 1 ? "text-terminal-muted" : "text-terminal-red";
                  const panelHeight = idx === 0 ? "border-terminal-yellow/30" : idx === 1 ? "border-terminal-muted/20" : "border-terminal-red/20";

                  return (
                    <div
                      key={char.token_id}
                      className={`panel p-4 text-center border-t-2 ${panelHeight} ${
                        renderIdx === 1 ? "order-first" : renderIdx === 2 ? "order-last" : ""
                      }`}
                    >
                      <div className={`text-2xl font-bold ${medalColor}`}>#{idx + 1}</div>
                      <img
                        src={char.image_url || "/placeholder.png"}
                        alt={char.name}
                        className="w-16 h-16 mx-auto my-2 rounded-full border border-terminal-border object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
                      />
                      <div className={`text-sm font-mono font-bold truncate ${color}`}>{char.name}</div>
                      <div className="text-[10px] font-mono text-terminal-muted">{char.class_name} Lv.{char.level}</div>
                      <div className="text-xl font-mono font-black text-terminal-green mt-1">
                        {char.cp?.toLocaleString()}
                      </div>
                      <div className="text-[10px] font-mono text-terminal-muted">CP</div>
                    </div>
                  );
                })}
              </div>
            );
          })()}

          {/* Class table */}
          <div className="panel">
            <div className="panel-header flex items-center justify-between border-b border-terminal-border/50 pb-2">
              <span className="panel-title">
                {activeClass === "all" ? "ALL CLASSES" : activeClass.toUpperCase()}
              </span>
              <span className="text-[10px] font-mono text-terminal-muted">
                {(activeClass === "all" ? allChars : (classGroups[activeClass] || []))?.length} characters
              </span>
            </div>

            {classLoading ? (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm">
                Loading data...
              </div>
            ) : allChars.length === 0 ? (
              <div className="p-8 text-center text-terminal-muted font-mono text-sm">
                No data available — enable services to scan and enrich characters
              </div>
            ) : (
              <ClassTable
                chars={activeClass === "all" ? allChars : (classGroups[activeClass] || [])}
              />
            )}
          </div>
        </>
      )}

      {/* ===== JOB VIEW ===== */}
      {activeTab === "job" && (
        <>
          {/* Job filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveJob(null)}
              className={`px-3 py-1.5 text-[10px] font-mono rounded border transition-all ${
                activeJob === null
                  ? "bg-terminal-accent/10 text-terminal-accent border-terminal-accent/40"
                  : "text-terminal-muted border-terminal-border hover:text-terminal-text"
              }`}
            >
              ALL JOBS
            </button>
            {jobsLoading ? (
              <span className="text-[10px] font-mono text-terminal-muted py-1.5">Loading...</span>
            ) : (jobs || []).map((job: JobInfo) => (
              <button
                key={job.job_name}
                onClick={() => setActiveJob(job.job_name)}
                className={`px-3 py-1.5 text-[10px] font-mono rounded border transition-all ${
                  activeJob === job.job_name
                    ? "bg-terminal-accent/10 text-terminal-accent border-terminal-accent/40"
                    : "text-terminal-muted border-terminal-border hover:text-terminal-text"
                }`}
              >
                {job.job_name} ({job.count})
              </button>
            ))}
          </div>

          {/* Top 10 highlight cards */}
          {jobTop10.length >= 3 && (
            <>
              <div className="panel">
                <div className="panel-header border-b border-terminal-border/50 pb-2">
                  <span className="panel-title text-terminal-yellow">
                    {activeJob ? `TOP 10 — ${activeJob}` : "TOP 10 ALL JOBS"}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-3 p-4">
                  {jobTop10.slice(0, 5).map((char, i) => (
                    <TopCard key={char.token_id} char={char} rank={i + 1} />
                  ))}
                </div>
                <div className="grid grid-cols-5 gap-3 px-4 pb-4">
                  {jobTop10.slice(5, 10).map((char, i) => (
                    <TopCard key={char.token_id} char={char} rank={i + 6} />
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header flex items-center justify-between border-b border-terminal-border/50 pb-2">
                  <span className="panel-title">
                    {activeJob ? activeJob.toUpperCase() : "ALL JOBS"} — FULL LIST
                  </span>
                  <span className="text-[10px] font-mono text-terminal-muted">
                    {jobAll.length} / {jobTotal.toLocaleString()} total
                  </span>
                </div>
                <JobTable chars={jobAll} />
              </div>
            </>
          )}

          {jobTop10.length === 0 && !jobLoading && (
            <div className="panel p-8 text-center text-terminal-muted font-mono text-sm">
              No job data available — enable services to scan and enrich characters
            </div>
          )}

          {jobLoading && (
            <div className="panel p-8 text-center text-terminal-muted font-mono text-sm">
              Loading job data...
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────

interface JobEntry {
  token_id: string;
  name: string;
  class_name: string;
  job_name: string;
  level: number;
  combat_power: number;
  char_att: number;
  char_matt: number;
  image_url: string | null;
  source: string;
}

function TopCard({ char, rank }: { char: JobEntry; rank: number }) {
  const classType = getClassType(char.class_name);
  const color = CLASS_COLORS[classType] || "text-terminal-text";
  const isTop3 = rank <= 3;
  const medalColor = rank === 1 ? "text-terminal-yellow" : rank === 2 ? "text-terminal-muted" : rank === 3 ? "text-terminal-red" : "";

  return (
    <div className={`panel p-3 text-center ${isTop3 ? `border-t-2 ${rank === 1 ? "border-terminal-yellow/30" : rank === 2 ? "border-terminal-muted/20" : "border-terminal-red/20"}` : "border border-terminal-border/30"}`}>
      <div className={`text-lg font-bold ${medalColor}`}>#{rank}</div>
      <img
        src={char.image_url || "/placeholder.png"}
        alt={char.name}
        className="w-12 h-12 mx-auto my-1 rounded-full border border-terminal-border object-cover"
        onError={(e) => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
      />
      <div className={`text-xs font-mono font-bold truncate ${color}`}>{char.name}</div>
      <div className="text-[9px] font-mono text-terminal-muted">
        {char.job_name} · {char.class_name} Lv.{char.level}
      </div>
      <div className="text-sm font-mono font-black text-terminal-green mt-1">
        {char.combat_power.toLocaleString()}
      </div>
      <div className="text-[9px] font-mono text-terminal-muted">CP</div>
    </div>
  );
}

function ClassTable({ chars }: { chars: LeaderboardEntry[] }) {
  if (chars.length === 0) return (
    <div className="p-8 text-center text-terminal-muted font-mono text-sm">
      No data available
    </div>
  );

  return (
    <div className="overflow-y-auto max-h-[800px]">
      <div className="grid grid-cols-12 gap-2 px-4 py-2 text-[10px] font-mono text-terminal-muted border-b border-terminal-border/30">
        <div className="col-span-1">RANK</div>
        <div className="col-span-4">NAME</div>
        <div className="col-span-2 text-center">CLASS</div>
        <div className="col-span-1 text-center">LVL</div>
        <div className="col-span-2 text-right">PRICE</div>
        <div className="col-span-2 text-right">COMBAT POWER</div>
      </div>

      {chars.map((char, i) => {
        const classType = getClassType(char.class_name);
        const color = CLASS_COLORS[classType] || "text-terminal-text";
        const rankPrefix = i === 0 ? "text-terminal-yellow font-bold" : i === 1 ? "text-terminal-muted font-bold" : i === 2 ? "text-terminal-red font-bold" : "text-terminal-muted";

        return (
          <div
            key={char.token_id}
            className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-terminal-surface/50 border-b border-terminal-border/10"
          >
            <div className={`col-span-1 font-mono text-xs ${rankPrefix}`}>
              #{i + 1}
            </div>
            <div className="col-span-4 flex items-center gap-2">
              <img
                src={char.image_url || "/placeholder.png"}
                alt={char.name}
                className="w-8 h-8 rounded border border-terminal-border object-cover flex-shrink-0"
                onError={(e) => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
              />
              <span className="font-mono text-xs text-terminal-text truncate">{char.name}</span>
            </div>
            <div className={`col-span-2 text-center font-mono text-xs ${color}`}>
              {char.class_name}
            </div>
            <div className="col-span-1 text-center font-mono text-xs text-terminal-cyan">
              {char.level}
            </div>
            <div className="col-span-2 text-right font-mono text-xs text-terminal-accent">
              {char.price?.toLocaleString()}
            </div>
            <div className="col-span-2 text-right font-mono text-xs text-terminal-green font-bold">
              {(char.combat_power ?? char.cp)?.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function JobTable({ chars }: { chars: JobEntry[] }) {
  if (chars.length === 0) return (
    <div className="p-8 text-center text-terminal-muted font-mono text-sm">
      No data — waiting for enrichment pipeline
    </div>
  );

  return (
    <div className="overflow-y-auto max-h-[800px]">
      <div className="grid grid-cols-12 gap-2 px-4 py-2 text-[10px] font-mono text-terminal-muted border-b border-terminal-border/30">
        <div className="col-span-1">RANK</div>
        <div className="col-span-3">NAME</div>
        <div className="col-span-2 text-center">JOB</div>
        <div className="col-span-2 text-center">CLASS</div>
        <div className="col-span-1 text-center">LVL</div>
        <div className="col-span-3 text-right">COMBAT POWER</div>
      </div>

      {chars.map((char, i) => {
        const classType = getClassType(char.class_name);
        const color = CLASS_COLORS[classType] || "text-terminal-text";
        const rankPrefix = i === 0 ? "text-terminal-yellow font-bold" : i === 1 ? "text-terminal-muted font-bold" : i === 2 ? "text-terminal-red font-bold" : "text-terminal-muted";

        return (
          <div
            key={char.token_id}
            className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-terminal-surface/50 border-b border-terminal-border/10"
          >
            <div className={`col-span-1 font-mono text-xs ${rankPrefix}`}>
              #{i + 1}
            </div>
            <div className="col-span-3 flex items-center gap-2">
              <img
                src={char.image_url || "/placeholder.png"}
                alt={char.name}
                className="w-8 h-8 rounded border border-terminal-border object-cover flex-shrink-0"
                onError={(e) => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
              />
              <span className="font-mono text-xs text-terminal-text truncate">{char.name}</span>
            </div>
            <div className="col-span-2 text-center font-mono text-xs text-terminal-accent">
              {char.job_name}
            </div>
            <div className={`col-span-2 text-center font-mono text-xs ${color}`}>
              {char.class_name}
            </div>
            <div className="col-span-1 text-center font-mono text-xs text-terminal-cyan">
              {char.level}
            </div>
            <div className="col-span-3 text-right font-mono text-xs text-terminal-green font-bold">
              {char.combat_power.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}
