import { useEffect, useState } from "react";
import { AlertEvent } from "../types";

interface DisplayAlert extends AlertEvent {
  uid: number;
}

interface Props {
  newAlerts: AlertEvent[];
}

let uidCounter = 0;

export default function AlertBanner({ newAlerts }: Props) {
  const [alerts, setAlerts] = useState<DisplayAlert[]>([]);

  useEffect(() => {
    if (!newAlerts.length) return;
    setAlerts((prev) => [
      ...newAlerts.map((a) => ({ ...a, uid: ++uidCounter })),
      ...prev,
    ]);
  }, [newAlerts]);

  // Auto-dismiss oldest after 10 s
  useEffect(() => {
    if (!alerts.length) return;
    const timer = setTimeout(() => setAlerts((prev) => prev.slice(0, -1)), 10_000);
    return () => clearTimeout(timer);
  }, [alerts]);

  const dismiss = (uid: number) =>
    setAlerts((prev) => prev.filter((a) => a.uid !== uid));

  return (
    <div className="ds-card">
      <div className="ds-card-title" style={{ color: "#FCA5A5" }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        Alertas de velocidade
      </div>

      {alerts.length === 0 ? (
        <p style={{ color: "var(--fg3)", fontSize: 13, textAlign: "center", padding: "6px 0" }}>
          Nenhum alerta
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 200, overflowY: "auto" }}>
          {alerts.map((a) => (
            <div key={a.uid} className="ds-alert-row">
              <span>
                <strong>Caminhão #{a.truck_id}</strong> — {a.speed_kmh.toFixed(1)} km/h{" "}
                <span style={{ color: "var(--fg3)", fontSize: 11, marginLeft: 6 }}>
                  (limite: {a.threshold_kmh} km/h ·{" "}
                  {new Date(a.timestamp * 1000).toLocaleTimeString("pt-BR")})
                </span>
              </span>
              <button
                onClick={() => dismiss(a.uid)}
                style={{
                  background: "none", border: "none",
                  color: "rgba(252,165,165,0.6)", cursor: "pointer",
                  fontSize: 16, lineHeight: 1, flexShrink: 0,
                }}
                aria-label="Fechar alerta"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
