import asyncio
import json
import time

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.detector import SpeedDetector

app = FastAPI(title="Truck Speed Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton — mantém estado do rastreador entre frames
detector = SpeedDetector()


async def _detection_loop(queue: asyncio.Queue) -> None:
    """
    Roda em background: captura frames RTSP, processa e empurra para a queue.
    Reconnecta automaticamente se o stream cair.
    """
    loop = asyncio.get_event_loop()
    cap = None

    def open_cap() -> cv2.VideoCapture:
        c = cv2.VideoCapture(config.RTSP_URL, cv2.CAP_FFMPEG)
        if not c.isOpened():
            c = cv2.VideoCapture(config.RTSP_URL)
        return c

    try:
        cap = await loop.run_in_executor(None, open_cap)

        while True:
            ret, frame = await loop.run_in_executor(None, cap.read)

            if not ret:
                # Stream perdido — tenta reconectar
                cap.release()
                await asyncio.sleep(2)
                cap = await loop.run_in_executor(None, open_cap)
                continue

            msg = detector.process_frame(frame)

            # Descarta frame antigo se o frontend não consegue acompanhar
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            queue.put_nowait(msg)

    finally:
        if cap is not None:
            cap.release()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue(maxsize=2)

    # Inicia o loop de captura/detecção como task paralela
    detection_task = asyncio.ensure_future(_detection_loop(queue))

    try:
        while True:
            # Aguarda o que chegar primeiro: novo frame OU mensagem do cliente
            frame_future = asyncio.ensure_future(queue.get())
            recv_future = asyncio.ensure_future(websocket.receive_text())

            done, pending = await asyncio.wait(
                [frame_future, recv_future],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancela a tarefa que não completou
            for t in pending:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass

            for t in done:
                result = t.result()

                # Mensagem recebida do frontend (ex.: atualização de threshold)
                if isinstance(result, str):
                    try:
                        data = json.loads(result)
                        if data.get("type") == "set_threshold":
                            new_threshold = float(data["speed_threshold_kmh"])
                            detector.threshold_kmh = new_threshold
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass

                # Novo frame processado → envia ao frontend
                else:
                    await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        pass
    finally:
        detection_task.cancel()
        try:
            await detection_task
        except (asyncio.CancelledError, Exception):
            pass


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": time.time()}
