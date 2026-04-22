import { TruckData } from "../types";

interface Props {
  trucks: TruckData[];
  threshold: number;
}

function speedClass(speed: number, threshold: number) {
  if (speed >= threshold) return "over";
  if (speed >= threshold * 0.75) return "warn";
  return "ok";
}

export default function TruckTable({ trucks, threshold }: Props) {
  return (
    <div className="ds-card">
      <div className="ds-card-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="1" y="3" width="15" height="13" /><polygon points="16 8 20 8 23 11 23 16 16 16 16 8" /><circle cx="5.5" cy="18.5" r="2.5" /><circle cx="18.5" cy="18.5" r="2.5" />
        </svg>
        Caminhões ativos
      </div>

      {trucks.length === 0 ? (
        <p style={{ color: "var(--fg3)", fontSize: 13, textAlign: "center", padding: "14px 0" }}>
          Nenhum caminhão detectado
        </p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                {["ID", "Placa", "km/h", "ROI", "Alerta"].map((h, i) => (
                  <th
                    key={h}
                    style={{
                      textAlign: i === 2 ? "right" : i >= 3 ? "center" : "left",
                      padding: "8px 10px",
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
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
              {trucks.map((truck) => {
                const cls = speedClass(truck.speed_kmh, threshold);
                const speedColor =
                  cls === "over" ? "#F87171" : cls === "warn" ? "#FBBF24" : "#34D399";
                return (
                  <tr
                    key={truck.id}
                    style={{
                      background: truck.alert ? "rgba(239,68,68,0.08)" : undefined,
                    }}
                  >
                    <td
                      style={{
                        padding: "10px",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--fg1)",
                      }}
                    >
                      #{truck.id}
                    </td>
                    <td
                      style={{
                        padding: "10px",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        letterSpacing: "0.15em",
                        fontWeight: 700,
                        color: "#FCD34D",
                      }}
                    >
                      {truck.license_plate ?? (
                        <span style={{ color: "var(--fg3)", letterSpacing: "normal" }}>—</span>
                      )}
                    </td>
                    <td
                      style={{
                        padding: "10px",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        fontWeight: 800,
                        textAlign: "right",
                        color: speedColor,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {truck.speed_kmh.toFixed(1)}
                    </td>
                    <td
                      style={{
                        padding: "10px",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        textAlign: "center",
                        fontSize: 14,
                      }}
                    >
                      {truck.in_roi ? (
                        <span style={{ color: "#34D399" }}>✓</span>
                      ) : (
                        <span style={{ color: "var(--fg3)" }}>—</span>
                      )}
                    </td>
                    <td
                      style={{
                        padding: "10px",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        textAlign: "center",
                        fontSize: 14,
                      }}
                    >
                      {truck.alert ? (
                        <span style={{ color: "#F87171", fontWeight: 700 }}>⚠</span>
                      ) : (
                        <span style={{ color: "var(--fg3)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
