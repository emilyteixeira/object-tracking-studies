import { Stats } from "../types";

interface Props {
  stats: Stats | null;
}

function StatCard({
  label,
  value,
  unit,
  hero,
}: {
  label: string;
  value: string | number;
  unit?: string;
  hero?: boolean;
}) {
  return (
    <div className={`stat-card${hero ? " hero" : ""}`}>
      <span className="stat-lbl">{label}</span>
      <span className="stat-val">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </span>
    </div>
  );
}

export default function StatsPanel({ stats }: Props) {
  return (
    <div className="ds-card">
      <div className="ds-card-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        Estatísticas do sistema
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <StatCard label="Total detectados" value={stats?.total_seen ?? "—"} />
        <StatCard label="Ativos agora" value={stats?.active_count ?? "—"} />
        <StatCard
          label="Vel. média"
          value={stats ? stats.avg_speed_kmh.toFixed(1) : "—"}
          unit="km/h"
          hero
        />
        <StatCard
          label="Vel. máxima"
          value={stats ? stats.max_speed_kmh.toFixed(1) : "—"}
          unit="km/h"
        />
        <StatCard
          label="Vel. mínima"
          value={stats ? stats.min_speed_kmh.toFixed(1) : "—"}
          unit="km/h"
        />
        <StatCard label="FPS" value={stats ? stats.fps.toFixed(1) : "—"} />
      </div>
    </div>
  );
}
