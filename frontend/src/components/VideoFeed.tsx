import { useEffect, useRef, useState } from "react";
import { ConnectionStatus } from "../types";

interface Props {
  frame: string;
  status: ConnectionStatus;
  roiYMin?: number;
  roiYMax?: number;
}

interface CameraInfo {
  ip: string;
  channel: string;
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

export default function VideoFeed({ frame, status, roiYMin = 200, roiYMax = 600 }: Props) {
  const time = useClock();
  const imgRef = useRef<HTMLImageElement>(null);
  const [frameHeight, setFrameHeight] = useState(0);
  const [cameraInfo, setCameraInfo] = useState<CameraInfo>({ ip: "...", channel: "1" });

  useEffect(() => {
    fetch("/api/camera-info")
      .then((r) => r.json())
      .then((data: CameraInfo) => setCameraInfo(data))
      .catch(() => {});
  }, []);

  const handleImageLoad = () => {
    const h = imgRef.current?.naturalHeight ?? 0;
    if (h > 0 && h !== frameHeight) setFrameHeight(h);
  };

  const roiTop = frameHeight > 0 ? `${(roiYMin / frameHeight) * 100}%` : "44%";
  const roiHeight =
    frameHeight > 0 ? `${((roiYMax - roiYMin) / frameHeight) * 100}%` : "18%";

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
          ref={imgRef}
          src={`data:image/jpeg;base64,${frame}`}
          alt="Feed ao vivo"
          className="w-full h-auto block"
          onLoad={handleImageLoad}
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
        style={{ top: roiTop, height: roiHeight }}
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
        <span>RTSP · {cameraInfo.ip} · CH{cameraInfo.channel}</span>
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
