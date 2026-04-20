"""
PassageTracker: gerencia o ciclo de vida de cada passagem de caminhão pelo ROI.

Uma "passagem" começa quando um truck_id entra no ROI e termina quando:
  - O caminhão sai do ROI (in_roi muda para False), ou
  - O CentroidTracker desregistra o ID (caminhão desapareceu da cena).

Durante a passagem:
  - Rastreia a velocidade máxima registrada.
  - Roda OCR a cada PLATE_OCR_INTERVAL frames para detectar a placa.
  - Salva o snapshot do frame com a melhor leitura de placa.
  - Persiste tudo no SQLite ao fechar.
"""

import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from backend import config
from backend import database as db
from backend.plate_detector import PlateDetector


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PassageState:
    passage_id: int
    max_speed_kmh: float = 0.0
    best_plate: Optional[str] = None
    plate_confidence: float = 0.0
    best_frame_path: Optional[str] = None
    frames_in_roi: int = 0


class PassageTracker:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._active: Dict[int, PassageState] = {}  # truck_id → PassageState
        self._plate_detector = PlateDetector()

        # Garante que o diretório de snapshots existe
        os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)

    # ── API pública ───────────────────────────────────────────────────────────

    def process(
        self,
        truck_id: int,
        in_roi: bool,
        bbox: Optional[Tuple[int, int, int, int]],
        frame: np.ndarray,
        speed_kmh: float,
    ) -> None:
        """
        Chamado para cada caminhão rastreado a cada frame processado.
        Gerencia abertura/fechamento de passagens e dispara OCR.
        """
        if in_roi:
            self._ensure_open(truck_id)
            state = self._active[truck_id]

            # Atualiza velocidade máxima
            if speed_kmh > state.max_speed_kmh:
                state.max_speed_kmh = speed_kmh

            # OCR throttled
            if bbox and state.frames_in_roi % config.PLATE_OCR_INTERVAL == 0:
                self._try_ocr(truck_id, state, frame, bbox)

            state.frames_in_roi += 1

        else:
            # Caminhão saiu do ROI → fecha a passagem
            if truck_id in self._active:
                self._close(truck_id)

    def on_deregister(self, truck_id: int) -> None:
        """Chamado quando o CentroidTracker remove um ID (saiu da cena)."""
        if truck_id in self._active:
            self._close(truck_id)

    def get_best_plate(self, truck_id: int) -> Optional[str]:
        """Retorna a melhor placa lida até agora para um caminhão ativo."""
        state = self._active.get(truck_id)
        return state.best_plate if state else None

    # ── Internos ─────────────────────────────────────────────────────────────

    def _ensure_open(self, truck_id: int) -> None:
        if truck_id not in self._active:
            passage_id = db.open_passage(
                self._conn,
                truck_track_id=truck_id,
                entry_time=_now_iso(),
            )
            self._active[truck_id] = PassageState(passage_id=passage_id)

    def _close(self, truck_id: int) -> None:
        state = self._active.pop(truck_id)
        db.close_passage(
            self._conn,
            passage_id=state.passage_id,
            exit_time=_now_iso(),
            max_speed_kmh=state.max_speed_kmh if state.max_speed_kmh > 0 else None,
            best_plate=state.best_plate,
            plate_confidence=state.plate_confidence if state.best_plate else None,
            frame_path=state.best_frame_path,
        )

    def _try_ocr(
        self,
        truck_id: int,
        state: PassageState,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> None:
        """Roda OCR e, se a nova leitura for melhor, salva snapshot e atualiza o estado."""
        text, conf = self._plate_detector.read(frame, bbox)
        if text is None or conf <= state.plate_confidence:
            return

        state.best_plate = text
        state.plate_confidence = conf

        # Salva snapshot
        snap_path = self._save_snapshot(state.passage_id, truck_id, frame, bbox)
        state.best_frame_path = snap_path

        db.add_plate_read(
            self._conn,
            passage_id=state.passage_id,
            raw_text=text,
            confidence=conf,
            read_time=_now_iso(),
            frame_path=snap_path,
        )

    def _save_snapshot(
        self,
        passage_id: int,
        truck_id: int,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> str:
        """Salva o recorte do caminhão em disco e retorna o caminho relativo."""
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size == 0:
            crop = frame

        ts = int(time.time())
        filename = f"{passage_id}_{truck_id}_{ts}.jpg"
        path = os.path.join(config.SNAPSHOT_DIR, filename)
        cv2.imwrite(path, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return path
