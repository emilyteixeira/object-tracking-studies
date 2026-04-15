import { Stats } from "../types";

interface Props {
  stats: Stats | null;
}

function StatCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 flex flex-col gap-1">
      <span className="text-gray-400 text-xs uppercase tracking-wide">{label}</span>
      <span className="text-white text-xl font-bold">
        {value}
        {unit && <span className="text-gray-400 text-sm ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function StatsPanel({ stats }: Props) {
  if (!stats) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 text-gray-500 text-sm">
        Aguardando dados...
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Estatísticas</h2>
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Total detectado" value={stats.total_seen} />
        <StatCard label="Ativos agora" value={stats.active_count} />
        <StatCard label="Vel. média" value={stats.avg_speed_kmh} unit="km/h" />
        <StatCard label="Vel. máxima" value={stats.max_speed_kmh} unit="km/h" />
        <StatCard label="Vel. mínima" value={stats.min_speed_kmh} unit="km/h" />
        <StatCard label="FPS" value={stats.fps} />
      </div>
    </div>
  );
}
