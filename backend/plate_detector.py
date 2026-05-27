"""
Detecção de placa veicular em dois passos:
  1. YOLO (keremberke/yolov8n-license-plate-detection) localiza a região da placa
     dentro do recorte do caminhão.
  2. EasyOCR extrai o texto da região detectada.
  3. Regex filtra formatos de placa brasileira (antiga AAA-0000 e Mercosul AAA0A00).
"""

import re
from typing import Optional, Tuple

import cv2
import numpy as np
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

from backend import config


def _resolve_plate_model(model_path: str) -> str:
    """
    Resolve o caminho do modelo de placas.
    Se `model_path` parecer um repo HuggingFace (contém '/'), baixa o arquivo
    best.pt via hf_hub_download e retorna o caminho local em cache.
    Caso contrário (arquivo .pt local), retorna como está.
    """
    if model_path.endswith(".pt") or model_path.endswith(".onnx"):
        return model_path  # caminho local direto
    # Formato "owner/repo" → baixa best.pt do HuggingFace Hub
    return hf_hub_download(repo_id=model_path, filename="best.pt")

# Padrões de placa brasileira
_PLATE_PATTERNS = [
    re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$"),   # Mercosul: ABC1D23
    re.compile(r"^[A-Z]{3}[0-9]{4}$"),               # Antiga:   ABC1234
    re.compile(r"^[A-Z]{3}-?[0-9]{4}$"),             # Antiga com hífen: ABC-1234
]


def _is_valid_plate(text: str) -> bool:
    clean = re.sub(r"[\s\-]", "", text.upper())
    return any(p.match(clean) for p in _PLATE_PATTERNS)


class PlateDetector:
    def __init__(self) -> None:
        # Modelo YOLO para localizar região da placa
        resolved = _resolve_plate_model(config.PLATE_MODEL_PATH)
        self._plate_model = YOLO(resolved)

        # EasyOCR — inicializado uma única vez (lento na primeira chamada)
        import easyocr  # import tardio para não atrasar o startup se não instalado
        import torch
        self._ocr = easyocr.Reader(["pt", "en"], gpu=torch.cuda.is_available(), verbose=False)

    def read(
        self,
        frame: np.ndarray,
        truck_bbox: Tuple[int, int, int, int],
    ) -> Tuple[Optional[str], float]:
        """
        Detecta e lê a placa de um caminhão.

        Args:
            frame:      frame completo (BGR)
            truck_bbox: (x1, y1, x2, y2) do caminhão no frame

        Returns:
            (texto_placa, confiança) ou (None, 0.0) se nenhuma placa válida encontrada
        """
        x1, y1, x2, y2 = truck_bbox
        # Garante que o recorte está dentro dos limites do frame
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        truck_crop = frame[y1:y2, x1:x2]
        if truck_crop.size == 0:
            return None, 0.0

        # ── Passo 1: localizar placa com YOLO ────────────────────────────────
        results = self._plate_model(truck_crop, verbose=False, conf=0.3)[0]
        plate_crop = self._best_plate_crop(truck_crop, results)

        if plate_crop is None:
            # Fallback: tenta OCR direto no recorte do caminhão (câmera de alta res)
            plate_crop = truck_crop

        # ── Passo 2: OCR na região da placa ──────────────────────────────────
        # Upscale para melhorar precisão do OCR em imagens pequenas
        scale = max(1, 120 // max(plate_crop.shape[:2]))
        if scale > 1:
            plate_crop = cv2.resize(
                plate_crop,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )

        ocr_results = self._ocr.readtext(plate_crop, detail=1)

        # ── Passo 3: filtrar e retornar melhor leitura válida ─────────────────
        return self._best_valid_read(ocr_results)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _best_plate_crop(
        truck_crop: np.ndarray,
        yolo_results,
    ) -> Optional[np.ndarray]:
        """Retorna o recorte da placa com maior confiança, ou None."""
        boxes = yolo_results.boxes
        if boxes is None or len(boxes) == 0:
            return None

        confs = boxes.conf.cpu().numpy()
        best_i = int(confs.argmax())
        bx1, by1, bx2, by2 = boxes.xyxy[best_i].cpu().numpy().astype(int)

        h, w = truck_crop.shape[:2]
        bx1, by1 = max(0, bx1), max(0, by1)
        bx2, by2 = min(w, bx2), min(h, by2)

        crop = truck_crop[by1:by2, bx1:bx2]
        return crop if crop.size > 0 else None

    @staticmethod
    def _best_valid_read(ocr_results) -> Tuple[Optional[str], float]:
        """
        Percorre resultados do EasyOCR, normaliza o texto e retorna o
        primeiro que corresponde a um formato de placa brasileiro.
        """
        best_text: Optional[str] = None
        best_conf: float = 0.0

        for _bbox, text, conf in ocr_results:
            clean = re.sub(r"[\s\-\.]", "", text.upper())
            if _is_valid_plate(clean) and conf > best_conf:
                best_text = re.sub(r"[\s\.]", "", text.upper())  # mantém hífen opcional
                best_conf = float(conf)

        return best_text, best_conf
