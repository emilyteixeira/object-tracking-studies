import { useRef } from "react";
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
    <div className="min-h-screen bg-gray-950 text-white p-4">
      {/* Cabeçalho */}
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            Detecção de Velocidade — Caminhões
          </h1>
          <p className="text-gray-400 text-xs mt-0.5">
            Stream RTSP · YOLO11 · Rastreamento por centróide · OCR de placas
          </p>
        </div>
      </header>

      {/* Layout principal */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Coluna esquerda — feed de vídeo */}
        <div className="lg:flex-[2]">
          <VideoFeed frame={msg?.frame ?? ""} status={status} />
        </div>

        {/* Coluna direita — painel de controle */}
        <div className="lg:flex-[1] flex flex-col gap-4">
          <StatsPanel stats={msg?.stats ?? null} />

          <TruckTable trucks={msg?.trucks ?? []} />

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
