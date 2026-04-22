import { useEffect, useState } from "react";
import { ConnectionStatus } from "../types";

interface Props {
  frame: string;
  status: ConnectionStatus;
}

function useClock() {
  const [time, setTime] = useState("");
  useEffect(() => {
    const tick = () => {
      const d = new Date();
      const pad = (n: number) => String(n).padStart(2, "0");
      setTime(`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

export default function VideoFeed({ frame, status }: Props) {
  const time = useClock();

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{
        borderRadius: "var(--radius-xl)",
        border: "4px solid var(--bg3)",
        background: "#000",
        boxShadow: "var(--shadow-xl)",
      }}
    >
      {/* Video content */}
      {frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="Feed ao vivo"
          className="w-full h-auto block"
        />
      ) : (
        <div
          className="flex items-center justify-center"
          style={{
            aspectRatio: "16/9",
            background: "linear-gradient(180deg, #0a1220 0%, #1a2540 30%, #2a3550 60%, #151e30 100%)",
          }}
        >
          <span style={{ color: "var(--fg3)", fontSize: 14 }}>
            {status === "connecting" ? "Conectando..." : "Aguardando stream..."}
          </span>
        </div>
      )}

      {/* ROI band overlay */}
      <div
        className="roi-band"
        style={{ top: "44%", height: "18%" }}
      >
        <span className="roi-label">Zona de medição</span>
      </div>

      {/* Top bar: LIVE badge + camera meta */}
      <div
        className="absolute top-3 left-3 right-3 flex items-center justify-between"
        style={{ pointerEvents: "none" }}
      >
        <div className="live-badge">
          <div className="blink-dot" />
          LIVE
        </div>
        <div className="feed-meta">
          CAM01 · {time}
        </div>
      </div>

      {/* Bottom bar: camera info */}
      <div
        className="absolute bottom-3 left-3 right-3 flex items-center justify-between"
        style={{
          pointerEvents: "none",
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "rgba(255,255,255,0.75)",
        }}
      >
        <span>RTSP · 10.6.51.220</span>
        <span
          style={{
            background: "rgba(0,0,0,0.5)",
            padding: "3px 8px",
            borderRadius: 4,
          }}
        >
          {status === "connected" ? "● ONLINE" : status === "connecting" ? "○ CONECTANDO" : "✕ OFFLINE"}
        </span>
      </div>
    </div>
  );
}
