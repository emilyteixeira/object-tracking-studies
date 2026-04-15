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

  // Adiciona novos alertas quando chegam
  useEffect(() => {
    if (!newAlerts.length) return;
    setAlerts((prev) => [
      ...newAlerts.map((a) => ({ ...a, uid: ++uidCounter })),
      ...prev,
    ]);
  }, [newAlerts]);

  // Auto-dismiss após 10 segundos
  useEffect(() => {
    if (!alerts.length) return;
    const timer = setTimeout(() => {
      setAlerts((prev) => prev.slice(0, -1));
    }, 10_000);
    return () => clearTimeout(timer);
  }, [alerts]);

  const dismiss = (uid: number) =>
    setAlerts((prev) => prev.filter((a) => a.uid !== uid));

  if (!alerts.length) return null;

  return (
    <div className="space-y-2">
      <h2 className="text-red-400 font-semibold text-sm uppercase tracking-wide">
        Alertas de velocidade
      </h2>
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {alerts.map((a) => (
          <div
            key={a.uid}
            className="flex items-center justify-between bg-red-900/60 border border-red-700 rounded-lg px-3 py-2 text-sm"
          >
            <span className="text-red-200">
              <span className="font-bold">Caminhão #{a.truck_id}</span> ultrapassou{" "}
              {a.threshold_kmh} km/h —{" "}
              <span className="font-bold">{a.speed_kmh.toFixed(1)} km/h</span>{" "}
              às {new Date(a.timestamp * 1000).toLocaleTimeString("pt-BR")}
            </span>
            <button
              onClick={() => dismiss(a.uid)}
              className="ml-2 text-red-400 hover:text-white transition-colors"
              aria-label="Fechar alerta"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
