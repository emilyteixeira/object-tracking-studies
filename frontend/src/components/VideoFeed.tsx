import { ConnectionStatus } from "../types";

interface Props {
  frame: string;
  status: ConnectionStatus;
}

export default function VideoFeed({ frame, status }: Props) {
  return (
    <div className="relative w-full rounded-lg overflow-hidden bg-gray-900 border border-gray-700">
      {frame ? (
        <img
          src={`data:image/jpeg;base64,${frame}`}
          alt="Feed ao vivo"
          className="w-full h-auto block"
        />
      ) : (
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
          {status === "connecting" ? "Conectando..." : "Aguardando stream..."}
        </div>
      )}

      {/* Badge de status sobreposto */}
      <span
        className={`absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-semibold ${
          status === "connected"
            ? "bg-green-600 text-white"
            : status === "connecting"
            ? "bg-yellow-500 text-black"
            : "bg-red-600 text-white"
        }`}
      >
        {status === "connected"
          ? "Conectado"
          : status === "connecting"
          ? "Conectando…"
          : "Desconectado"}
      </span>
    </div>
  );
}
