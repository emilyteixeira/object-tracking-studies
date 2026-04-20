import { useState } from "react";
import { TruckHistoryRecord } from "../types";

interface Props {
  records: TruckHistoryRecord[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function HistoryTable({ records, loading, error, onRefresh }: Props) {
  const [lightbox, setLightbox] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-white font-semibold text-sm uppercase tracking-wide">
          Histórico de passagens
        </h2>
        <button
          onClick={onRefresh}
          className="text-gray-400 hover:text-white text-xs transition-colors"
          title="Atualizar"
        >
          ↻ Atualizar
        </button>
      </div>

      {error && (
        <p className="text-red-400 text-xs">{error}</p>
      )}

      {loading && !records.length ? (
        <p className="text-gray-500 text-sm">Carregando...</p>
      ) : records.length === 0 ? (
        <p className="text-gray-500 text-sm">Nenhuma passagem registrada ainda.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-700 max-h-64 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-800 text-gray-400 uppercase sticky top-0">
              <tr>
                <th className="px-2 py-2 text-left">Entrada</th>
                <th className="px-2 py-2 text-left">Saída</th>
                <th className="px-2 py-2 text-left">Placa</th>
                <th className="px-2 py-2 text-right">Conf.</th>
                <th className="px-2 py-2 text-right">Vel. máx.</th>
                <th className="px-2 py-2 text-center">Foto</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.id}
                  className="border-t border-gray-700 bg-gray-900 hover:bg-gray-800 transition-colors"
                >
                  <td className="px-2 py-1.5 text-gray-300 font-mono">
                    {formatTime(r.entry_time)}
                  </td>
                  <td className="px-2 py-1.5 text-gray-400 font-mono">
                    {formatTime(r.exit_time)}
                  </td>
                  <td className="px-2 py-1.5">
                    {r.license_plate ? (
                      <span className="text-yellow-300 font-bold tracking-widest">
                        {r.license_plate}
                      </span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-right text-gray-400">
                    {r.plate_confidence != null
                      ? `${(r.plate_confidence * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`px-2 py-1.5 text-right font-bold ${
                      (r.max_speed_kmh ?? 0) >= 80
                        ? "text-red-400"
                        : (r.max_speed_kmh ?? 0) >= 60
                        ? "text-orange-400"
                        : "text-green-400"
                    }`}
                  >
                    {r.max_speed_kmh != null
                      ? `${r.max_speed_kmh.toFixed(1)} km/h`
                      : "—"}
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    {r.frame_path ? (
                      <button
                        onClick={() =>
                          setLightbox(`/${r.frame_path!.replace(/\\/g, "/")}`)
                        }
                        className="text-blue-400 hover:text-blue-200 transition-colors"
                        title="Ver foto"
                      >
                        🖼
                      </button>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lightbox simples para foto do caminhão */}
      {lightbox && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
          onClick={() => setLightbox(null)}
        >
          <img
            src={lightbox}
            alt="Snapshot"
            className="max-w-[90vw] max-h-[80vh] rounded-lg shadow-2xl"
          />
          <button
            className="absolute top-4 right-4 text-white text-2xl"
            onClick={() => setLightbox(null)}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
