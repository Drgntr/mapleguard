interface ScarcityBadgeProps {
  score?: number;
  showLabel?: boolean;
}

export default function ScarcityBadge({ score, showLabel = false }: ScarcityBadgeProps) {
  if (score === undefined || score === null) {
    return <span className="text-terminal-muted text-xs font-mono">-</span>;
  }

  let color: string;
  let label: string;
  let bgClass: string;

  if (score >= 90) {
    color = "text-terminal-red";
    bgClass = "bg-terminal-red/10 border-terminal-red/30";
    label = "MYTHIC";
  } else if (score >= 75) {
    color = "text-terminal-yellow";
    bgClass = "bg-terminal-yellow/10 border-terminal-yellow/30";
    label = "LEGENDARY";
  } else if (score >= 60) {
    color = "text-terminal-purple";
    bgClass = "bg-terminal-purple/10 border-terminal-purple/30";
    label = "EPIC";
  } else if (score >= 40) {
    color = "text-terminal-cyan";
    bgClass = "bg-terminal-cyan/10 border-terminal-cyan/30";
    label = "RARE";
  } else {
    color = "text-terminal-muted";
    bgClass = "bg-terminal-surface border-terminal-border";
    label = "COMMON";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-mono font-medium ${color} ${bgClass}`}
    >
      <span className="tabular-nums">{score.toFixed(1)}</span>
      {showLabel && <span className="text-[9px] opacity-70">{label}</span>}
    </span>
  );
}
