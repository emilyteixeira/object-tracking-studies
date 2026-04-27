import { useRef } from "react";
import ianorthLogo from "./assets/ianorth-logo.svg";
import AlertBanner from "./components/AlertBanner";
import HistoryTable from "./components/HistoryTable";
import StatsPanel from "./components/StatsPanel";
import ThresholdControl from "./components/ThresholdControl";
import TruckTable from "./components/TruckTable";
import VideoFeed from "./components/VideoFeed";
import { useHistory } from "./hooks/useHistory";
import { useWebSocket } from "./hooks/useWebSocket";
import { AlertEvent } from "./types";

export default function App() {
  const { latestMessage, status, sendThreshold } = useWebSocket();
  const { records, loading, error, refresh } = useHistory(100);

  const pendingAlerts = useRef<AlertEvent[]>([]);
  if (latestMessage?.alerts.length) {
    pendingAlerts.current = latestMessage.alerts;
  } else {
    pendingAlerts.current = [];
  }

  const msg = latestMessage;

  return (
    <div className="min-h-screen p-6" style={{ maxWidth: 1600, margin: "0 auto" }}>
      {/* Header */}
      <header className="glass-header rounded-2xl px-5 py-4 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={ianorthLogo} alt="IANorth" style={{ height: 40, width: "auto" }} />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              IANorth{" "}
              <span style={{ color: "var(--accent-primary)", fontWeight: 300 }}>
                | Detecção de Velocidade
              </span>
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--fg2)" }}>
              Monitoramento de caminhões em tempo real
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`status-pill${
              status === "connecting" ? " warn" : status === "disconnected" ? " err" : ""
            }`}
          >
            <span className="dot" />
            {status === "connected"
              ? "Conectado"
              : status === "connecting"
              ? "Conectando..."
              : "Desconectado"}
          </span>
        </div>
      </header>

      {/* Main layout: video left (2fr) + panels right (1fr) */}
      <div
        className="grid gap-5 items-start"
        style={{ gridTemplateColumns: "minmax(0,2fr) minmax(0,1fr)" }}
      >
        {/* Video feed */}
        <div style={{ position: "sticky", top: 20 }}>
          <VideoFeed
            frame={msg?.frame ?? ""}
            status={status}
            roiYMin={msg?.config.roi_y_min ?? 200}
            roiYMax={msg?.config.roi_y_max ?? 600}
          />
        </div>

        {/* Right panels */}
        <div className="flex flex-col gap-4">
          <StatsPanel stats={msg?.stats ?? null} />
          <TruckTable trucks={msg?.trucks ?? []} threshold={msg?.config.speed_threshold_kmh ?? 80} />
          <AlertBanner newAlerts={pendingAlerts.current} />
          <ThresholdControl
            currentThreshold={msg?.config.speed_threshold_kmh ?? 80}
            onSet={sendThreshold}
          />
          <HistoryTable
            records={records}
            loading={loading}
            error={error}
            onRefresh={refresh}
          />
        </div>
      </div>
    </div>
  );
}
