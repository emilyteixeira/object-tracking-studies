# ──────────────────────────────────────────────────────────────────────────────
# Configurações do sistema de detecção de velocidade de caminhões
# Edite este arquivo para calibrar a câmera e ajustar os parâmetros.
# ──────────────────────────────────────────────────────────────────────────────

# Fonte de vídeo RTSP (câmera IP)
RTSP_URL: str = "rtsp://admin:eletricasnb2021@10.6.51.220:554/cam/realmonitor?channel=1&subtype=1"

# Modelo YOLO (baixado automaticamente pelo ultralytics na primeira execução)
MODEL_PATH: str = "yolo11n.pt"

# Classe COCO para caminhão — NÃO alterar para lista; apenas caminhões são rastreados.
# Classes COCO: car=2, motorcycle=3, bus=5, truck=7
TRUCK_CLASS: int = 7

# Calibração: quantos metros correspondem a 1 pixel na cena
# Exemplo: se 10 metros na pista equivalem a 200 pixels → 10/200 = 0.05 m/px
METERS_PER_PIXEL: float = 10.0 / 200.0

# Região de interesse (eixo Y) onde a velocidade é medida
ROI_Y_MIN: int = 300
ROI_Y_MAX: int = 600

# Filtros de detecção
MIN_AREA: int = 400          # área mínima da bbox em pixels²
CONFIDENCE: float = 0.5      # confiança mínima do YOLO

# Rastreamento
MAX_DISAPPEARED: int = 20    # frames sem detecção antes de remover o objeto

# Limite de velocidade padrão para alertas (km/h)
DEFAULT_THRESHOLD_KMH: float = 80.0

# Qualidade JPEG para o stream de frames (0–100); menor = menos banda, mais artefatos
FRAME_JPEG_QUALITY: int = 75

# Tamanho da janela de média móvel para suavizar velocidade (frames)
SPEED_SMOOTHING_WINDOW: int = 5

# Histórico máximo de alertas mantido em memória
MAX_ALERT_HISTORY: int = 100

# ── Detecção de placas ────────────────────────────────────────────────────────
# Modelo YOLO para detecção de região de placa (baixado automaticamente do HuggingFace)
PLATE_MODEL_PATH: str = "keremberke/yolov8n-license-plate-detection"

# ── Banco de dados SQLite ─────────────────────────────────────────────────────
DB_PATH: str = "truck_history.db"

# Diretório para salvar snapshots dos caminhões (relativo à raiz do projeto)
SNAPSHOT_DIR: str = "snapshots"

# Identificador da câmera (útil para futuras instalações multi-câmera)
CAMERA_ID: str = "cam01"

# Intervalo de frames para rodar OCR dentro do ROI (throttle — OCR é lento)
PLATE_OCR_INTERVAL: int = 10
