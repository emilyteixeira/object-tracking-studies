from typing import List, Optional
from pydantic import BaseModel


class TruckData(BaseModel):
    id: int
    speed_kmh: float
    bbox: List[int]                    # [x1, y1, x2, y2]
    centroid: List[int]                # [cx, cy]
    in_roi: bool
    alert: bool
    license_plate: Optional[str] = None  # melhor leitura OCR até o momento


class Stats(BaseModel):
    total_seen: int
    active_count: int
    avg_speed_kmh: float
    max_speed_kmh: float
    min_speed_kmh: float
    fps: float


class AlertEvent(BaseModel):
    truck_id: int
    speed_kmh: float
    timestamp: float
    threshold_kmh: float


class ConfigData(BaseModel):
    speed_threshold_kmh: float
    roi_y_min: int
    roi_y_max: int
    meters_per_pixel: float


class FrameMessage(BaseModel):
    type: str = "frame"
    timestamp: float
    frame: str            # base64 JPEG
    trucks: List[TruckData]
    stats: Stats
    alerts: List[AlertEvent]
    config: ConfigData


class SetThresholdMessage(BaseModel):
    type: str = "set_threshold"
    speed_threshold_kmh: float


class TruckHistoryRecord(BaseModel):
    """Espelha a tabela truck_passages para a API REST."""
    id: int
    truck_track_id: int
    license_plate: Optional[str] = None
    plate_confidence: Optional[float] = None
    max_speed_kmh: Optional[float] = None
    entry_time: str
    exit_time: Optional[str] = None
    frame_path: Optional[str] = None
    camera_id: str
