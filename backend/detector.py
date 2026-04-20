import base64
import math
import sqlite3
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from backend import config
from backend import database as db
from backend.centroid_tracker import CentroidTracker
from backend.models import AlertEvent, ConfigData, FrameMessage, Stats, TruckData
from backend.passage_tracker import PassageTracker


class SpeedDetector:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.model = YOLO(config.MODEL_PATH)

        # Aquece o modelo para evitar latência no primeiro frame real
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy, verbose=False)

        self.ct = CentroidTracker(max_disappeared=config.MAX_DISAPPEARED)

        # last_pos: truck_id -> (cx, cy, frame_idx)
        self.last_pos: Dict[int, Tuple[int, int, int]] = {}

        # Média móvel de velocidade: truck_id -> deque de speeds
        self.speed_buffers: Dict[int, deque] = {}

        # Última velocidade conhecida por ID (para stats)
        self.speed_history: Dict[int, float] = {}

        # Alertas recentes
        self.alert_log: List[AlertEvent] = []

        # Limite de velocidade (pode ser alterado em tempo de execução via WebSocket)
        self.threshold_kmh: float = config.DEFAULT_THRESHOLD_KMH

        self._frame_idx: int = 0
        self._fps: float = 30.0
        self._last_time: float = time.time()

        # Histórico de passagens (SQLite + OCR de placas)
        self.passage_tracker = PassageTracker(conn)

    # ──────────────────────────────────────────────────────────────────────────
    # Método principal chamado para cada frame capturado
    # ──────────────────────────────────────────────────────────────────────────
    def process_frame(self, frame: np.ndarray) -> FrameMessage:
        self._frame_idx += 1

        # Calcula FPS em tempo real
        now = time.time()
        dt = now - self._last_time if (now - self._last_time) > 1e-6 else 1e-6
        self._fps = 1.0 / dt
        self._last_time = now

        # ── Detecção YOLO (apenas caminhões — classe 7) ──────────────────────
        results = self.model(frame, imgsz=640, conf=config.CONFIDENCE, verbose=False)[0]
        boxes = results.boxes

        rects: List[Tuple[int, int, int, int]] = []
        centroids: List[Tuple[int, int]] = []

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)
            for box, c in zip(xyxy, cls):
                if int(c) != config.TRUCK_CLASS:  # apenas caminhões
                    continue
                x1, y1, x2, y2 = box
                if (x2 - x1) * (y2 - y1) < config.MIN_AREA:
                    continue
                cx = int((x1 + x2) / 2)
                cy = int(y2)              # base da bbox como centróide Y
                rects.append((int(x1), int(y1), int(x2), int(y2)))
                centroids.append((cx, cy))

        # ── Rastreamento — captura IDs antes do update para detectar desregistros
        prev_ids = set(self.ct.objects.keys())
        objects = self.ct.update(centroids)
        deregistered_ids = prev_ids - set(objects.keys())

        # Notifica o PassageTracker sobre IDs que saíram da cena
        for tid in deregistered_ids:
            self.passage_tracker.on_deregister(tid)

        # ── Cálculo de velocidade e anotação ────────────────────────────────
        annotated = frame.copy()
        truck_data_list: List[TruckData] = []
        frame_alerts: List[AlertEvent] = []

        for object_id, centroid in objects.items():
            cx, cy = centroid
            raw_speed = 0.0
            in_roi = config.ROI_Y_MIN <= cy <= config.ROI_Y_MAX

            # Busca bbox mais próxima do centróide
            best_idx: Optional[int] = None
            best_dist = float("inf")
            for i, c in enumerate(centroids):
                d = math.hypot(cx - c[0], cy - c[1])
                if d < best_dist:
                    best_dist = d
                    best_idx = i

            bbox = rects[best_idx] if best_idx is not None and best_idx < len(rects) else None

            if in_roi:
                if object_id in self.last_pos:
                    last_cx, last_cy, last_f = self.last_pos[object_id]
                    df = self._frame_idx - last_f
                    if df > 0:
                        dpx = math.hypot(cx - last_cx, cy - last_cy)
                        dt_frames = df / max(self._fps, 1e-6)
                        raw_speed = (dpx * config.METERS_PER_PIXEL / dt_frames) * 3.6
                self.last_pos[object_id] = (cx, cy, self._frame_idx)

            # Média móvel para suavizar a velocidade
            if object_id not in self.speed_buffers:
                self.speed_buffers[object_id] = deque(maxlen=config.SPEED_SMOOTHING_WINDOW)
            if raw_speed > 0:
                self.speed_buffers[object_id].append(raw_speed)

            buf = self.speed_buffers[object_id]
            smooth_speed = float(np.mean(buf)) if buf else 0.0
            self.speed_history[object_id] = smooth_speed

            is_alert = smooth_speed > self.threshold_kmh and smooth_speed > 0

            # Registra alerta
            if is_alert:
                alert = AlertEvent(
                    truck_id=object_id,
                    speed_kmh=round(smooth_speed, 1),
                    timestamp=now,
                    threshold_kmh=self.threshold_kmh,
                )
                frame_alerts.append(alert)
                self.alert_log.append(alert)
                if len(self.alert_log) > config.MAX_ALERT_HISTORY:
                    self.alert_log.pop(0)

            # ── Atualiza PassageTracker ───────────────────────────────────────
            self.passage_tracker.process(
                truck_id=object_id,
                in_roi=in_roi,
                bbox=bbox,
                frame=frame,          # frame original (sem anotações) para melhor OCR
                speed_kmh=smooth_speed,
            )

            # Placa mais recente conhecida para este caminhão
            plate = self.passage_tracker.get_best_plate(object_id)

            # Cor da bbox por velocidade
            if smooth_speed >= 80:
                color = (0, 0, 255)    # vermelho
            elif smooth_speed >= 60:
                color = (0, 165, 255)  # laranja
            else:
                color = (0, 255, 0)    # verde

            # Anotação no frame
            if bbox:
                x1, y1, x2, y2 = bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                plate_label = f" [{plate}]" if plate else ""
                label = f"ID {object_id}{plate_label}  {smooth_speed:4.1f} km/h"
                cv2.putText(annotated, label, (x1, max(y1 - 6, 14)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                cv2.circle(annotated, (cx, cy), 5, color, -1)

                truck_data_list.append(TruckData(
                    id=object_id,
                    speed_kmh=round(smooth_speed, 1),
                    bbox=list(bbox),
                    centroid=[cx, cy],
                    in_roi=in_roi,
                    alert=is_alert,
                    license_plate=plate,
                ))

        # ROI e FPS no frame
        h, w = annotated.shape[:2]
        cv2.rectangle(annotated, (0, config.ROI_Y_MIN), (w, config.ROI_Y_MAX), (255, 0, 0), 2)
        cv2.putText(annotated, f"FPS {self._fps:4.1f}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        if frame_alerts:
            cv2.putText(annotated, "! VELOCIDADE EXCEDIDA", (10, 54),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ── Estatísticas globais ─────────────────────────────────────────────
        speeds = [s for s in self.speed_history.values() if s > 0]
        stats = Stats(
            total_seen=self.ct.next_object_id,
            active_count=len(objects),
            avg_speed_kmh=round(float(np.mean(speeds)), 1) if speeds else 0.0,
            max_speed_kmh=round(max(speeds), 1) if speeds else 0.0,
            min_speed_kmh=round(min(speeds), 1) if speeds else 0.0,
            fps=round(self._fps, 1),
        )

        # ── Codifica frame em JPEG base64 ────────────────────────────────────
        ok, buf = cv2.imencode(
            ".jpg", annotated,
            [cv2.IMWRITE_JPEG_QUALITY, config.FRAME_JPEG_QUALITY]
        )
        frame_b64 = base64.b64encode(buf).decode("utf-8") if ok else ""

        return FrameMessage(
            timestamp=now,
            frame=frame_b64,
            trucks=truck_data_list,
            stats=stats,
            alerts=frame_alerts,
            config=ConfigData(
                speed_threshold_kmh=self.threshold_kmh,
                roi_y_min=config.ROI_Y_MIN,
                roi_y_max=config.ROI_Y_MAX,
                meters_per_pixel=config.METERS_PER_PIXEL,
            ),
        )
