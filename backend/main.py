import asyncio
import json
import math
import os
import threading
import time

import cv2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend import database as db
from backend.detector import CALIBRATION_FILE, SpeedDetector

app = FastAPI(title="Truck Speed Detection API")

_extra_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
_cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"] + [o.strip() for o in _extra_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Banco de dados ────────────────────────────────────────────────────────────
_conn = db.init_db(config.DB_PATH)

# ── Detector (singleton) ──────────────────────────────────────────────────────
detector = SpeedDetector(conn=_conn)

# ── Servir snapshots como arquivos estáticos ──────────────────────────────────
os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=config.SNAPSHOT_DIR), name="snapshots")


# ──────────────────────────────────────────────────────────────────────────────
# RTSPReader: thread dedicada que lê o stream continuamente e guarda apenas
# o frame mais recente. Desacopla RTSP de YOLO — os dois nunca se bloqueiam.
# ──────────────────────────────────────────────────────────────────────────────
class RTSPReader:
    def __init__(self, url: str) -> None:
        self._url = url
        self._frame = None
        self._counter = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="rtsp-reader")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def get_latest(self):
        with self._lock:
            return self._counter, self._frame

    def _open(self) -> cv2.VideoCapture:
        # TCP evita perda de pacotes UDP que causa "Could not find ref with POC" em HEVC
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|"
            "stimeout;5000000|"       # timeout de conexão: 5 s
            "fflags;nobuffer|"
            "flags;low_delay"
        )
        cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
            cap = cv2.VideoCapture(self._url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, config.FPS)
        return cap

    def _loop(self) -> None:
        cap = self._open()
        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                cap.release()
                time.sleep(2)
                cap = self._open()
                continue
            with self._lock:
                self._frame = frame
                self._counter += 1
        cap.release()


_rtsp_reader = RTSPReader(config.RTSP_URL)


@app.on_event("startup")
async def startup() -> None:
    _rtsp_reader.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    _rtsp_reader.stop()


# ──────────────────────────────────────────────────────────────────────────────
# Loop de detecção
# ──────────────────────────────────────────────────────────────────────────────
async def _detection_loop(queue: asyncio.Queue) -> None:
    loop = asyncio.get_event_loop()
    last_counter = -1

    while True:
        counter, frame = _rtsp_reader.get_latest()

        if frame is None or counter == last_counter:
            await asyncio.sleep(0.01)
            continue

        last_counter = counter
        msg = await loop.run_in_executor(None, detector.process_frame, frame.copy())

        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        queue.put_nowait(msg)


# ──────────────────────────────────────────────────────────────────────────────
# Loop de recepção WebSocket
# ──────────────────────────────────────────────────────────────────────────────
async def _recv_loop(websocket: WebSocket) -> None:
    async for text in websocket.iter_text():
        try:
            data = json.loads(text)
            if data.get("type") == "set_threshold":
                detector.threshold_kmh = float(data["speed_threshold_kmh"])
        except (json.JSONDecodeError, KeyError, ValueError):
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint WebSocket
# ──────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue(maxsize=2)
    detection_task = asyncio.ensure_future(_detection_loop(queue))
    recv_task = asyncio.ensure_future(_recv_loop(websocket))

    try:
        while True:
            get_future = asyncio.ensure_future(queue.get())

            done, _ = await asyncio.wait(
                [get_future, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if recv_task in done:
                get_future.cancel()
                try:
                    await get_future
                except (asyncio.CancelledError, Exception):
                    pass
                break

            msg = get_future.result()
            try:
                await websocket.send_text(msg.model_dump_json())
            except (WebSocketDisconnect, RuntimeError):
                break

    except WebSocketDisconnect:
        pass
    finally:
        detection_task.cancel()
        recv_task.cancel()
        for t in (detection_task, recv_task):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


# ──────────────────────────────────────────────────────────────────────────────
# REST endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/history")
async def get_history(limit: int = 100):
    """Retorna as últimas `limit` passagens de caminhões."""
    return db.get_history(_conn, limit=limit)


class CalibrateRequest(BaseModel):
    meters_per_pixel: float | None = None
    px1: list[int] | None = None   # [x, y]
    px2: list[int] | None = None   # [x, y]
    real_meters: float | None = None


@app.post("/api/calibrate")
def calibrate(req: CalibrateRequest):
    """Atualiza a calibração meters_per_pixel em tempo real.

    Opção 1 — valor direto:     { "meters_per_pixel": 0.000264 }
    Opção 2 — dois pontos:      { "px1": [x1,y1], "px2": [x2,y2], "real_meters": 15.0 }
    """
    if req.meters_per_pixel is not None:
        mpp = req.meters_per_pixel
    elif req.px1 and req.px2 and req.real_meters:
        pixel_dist = math.hypot(req.px2[0] - req.px1[0], req.px2[1] - req.px1[1])
        if pixel_dist == 0:
            raise HTTPException(status_code=400, detail="px1 e px2 não podem ser o mesmo ponto")
        mpp = req.real_meters / pixel_dist
    else:
        raise HTTPException(
            status_code=400,
            detail="Forneça 'meters_per_pixel' ou 'px1' + 'px2' + 'real_meters'",
        )

    detector.meters_per_pixel = mpp
    with open(CALIBRATION_FILE, "w") as f:
        json.dump({"meters_per_pixel": mpp}, f)

    return {"meters_per_pixel": mpp}


@app.get("/api/camera-info")
def camera_info():
    """Retorna IP e canal da câmera sem expor credenciais."""
    import re
    m = re.search(r"@([\d.]+):\d+/[^?]*\??(.*)$", config.RTSP_URL)
    ip = m.group(1) if m else "unknown"
    params = dict(p.split("=", 1) for p in m.group(2).split("&") if "=" in p) if m else {}
    return {"ip": ip, "channel": params.get("channel", "1")}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": time.time()}


# ── Frontend (SPA) — deve ficar DEPOIS de todos os endpoints da API ───────────
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="spa-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str = "") -> FileResponse:
        index = os.path.join(_DIST, "index.html")
        return FileResponse(index)
