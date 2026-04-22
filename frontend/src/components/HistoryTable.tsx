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
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function speedColor(speed: number | null): string {
  if (speed == null) return "var(--fg3)";
  if (speed >= 80) return "#F87171";
  if (speed >= 60) return "#FBBF24";
  return "#34D399";
}

export default function HistoryTable({ records, loading, error, onRefresh }: Props) {
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = () => {
    setSpinning(true);
    setTimeout(() => setSpinning(false), 800);
    onRefresh();
  };

  return (
    <div className="ds-card">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div className="ds-card-title" style={{ margin: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="21 8 21 21 3 21 3 8" /><rect x="1" y="3" width="22" height="5" /><line x1="10" y1="12" x2="14" y2="12" />
          </svg>
          Histórico de passagens
        </div>
        <button
          className={`refresh-btn${spinning ? " spinning" : ""}`}
          onClick={handleRefresh}
          title="Atualizar"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          Atualizar
        </button>
      </div>

      {error && (
        <p style={{ color: "#F87171", fontSize: 12, marginBottom: 8 }}>{error}</p>
      )}

      {loading && !records.length ? (
        <p style={{ color: "var(--fg3)", fontSize: 13, padding: "10px 0" }}>Carregando...</p>
      ) : records.length === 0 ? (
        <p style={{ color: "var(--fg3)", fontSize: 13, padding: "10px 0" }}>
          Nenhuma passagem registrada ainda.
        </p>
      ) : (
        <div
          style={{
            maxHeight: 320, overflowY: "auto",
            border: "1px solid var(--bg3)",
            borderRadius: 8,
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr>
                {["Entrada", "Saída", "Placa", "Conf.", "Vel. máx.", "Foto"].map((h, i) => (
                  <th
                    key={h}
                    style={{
                      position: "sticky", top: 0, zIndex: 1,
                      textAlign: i >= 3 ? "right" : "left",
                      padding: "8px 10px",
                      fontSize: 10, fontWeight: 700,
                      textTransform: "uppercase", letterSpacing: "0.1em",
                      color: "var(--fg2)",
                      background: "rgba(0,0,0,0.25)",
                      borderBottom: "1px solid var(--bg3)",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.id}
                  style={{
                    background:
                      (r.max_speed_kmh ?? 0) >= 80
                        ? "rgba(239,68,68,0.06)"
                        : undefined,
                  }}
                >
                  <td style={tdStyle}>{formatTime(r.entry_time)}</td>
                  <td style={{ ...tdStyle, color: "var(--fg3)" }}>{formatTime(r.exit_time)}</td>
                  <td style={{ ...tdStyle, letterSpacing: "0.12em", fontWeight: 700, color: "#FCD34D" }}>
                    {r.license_plate ?? <span style={{ color: "var(--fg3)", letterSpacing: "normal" }}>—</span>}
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "var(--fg3)" }}>
                    {r.plate_confidence != null ? `${(r.plate_confidence * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right", fontWeight: 800, color: speedColor(r.max_speed_kmh) }}>
                    {r.max_speed_kmh != null ? `${r.max_speed_kmh.toFixed(1)}` : "—"}
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>
                    {r.frame_path ? (
                      <button
                        onClick={() => setLightbox(`/${r.frame_path!.replace(/\\/g, "/")}`)}
                        style={{ background: "none", border: "none", color: "#60A5FA", cursor: "pointer", fontSize: 14 }}
                        title="Ver foto"
                      >
                        🖼
                      </button>
                    ) : (
                      <span style={{ color: "var(--fg3)" }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {lightbox && (
        <div
          style={{
            position: "fixed", inset: 0,
            background: "rgba(0,0,0,0.85)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 50,
          }}
          onClick={() => setLightbox(null)}
        >
          <img
            src={lightbox}
            alt="Snapshot"
            style={{ maxWidth: "90vw", maxHeight: "80vh", borderRadius: 12, boxShadow: "0 20px 60px rgba(0,0,0,0.8)" }}
          />
          <button
            style={{
              position: "absolute", top: 16, right: 16,
              background: "none", border: "none", color: "#fff",
              fontSize: 24, cursor: "pointer",
            }}
            onClick={() => setLightbox(null)}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

const tdStyle: React.CSSProperties = {
  padding: "9px 10px",
  borderBottom: "1px solid rgba(255,255,255,0.04)",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  color: "var(--fg1)",
};
