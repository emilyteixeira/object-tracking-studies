# ──────────────────────────────────────────────────────────────────────────────
# Configurações do sistema de detecção de velocidade de caminhões
# Edite este arquivo para calibrar a câmera e ajustar os parâmetros.
# ──────────────────────────────────────────────────────────────────────────────

# Fonte de vídeo RTSP (câmera IP)
RTSP_URL: str = "rtsp://admin:eletricasnb2021@10.6.51.206:554/cam/realmonitor?channel=1&subtype=1"

# Modelo YOLO — use "yolo11n.pt" inicialmente; após rodar export_tensorrt.py troque por "yolo11n.engine"
MODEL_PATH: str = "yolo11n.engine"

# Classe COCO para caminhão — NÃO alterar para lista; apenas caminhões são rastreados.
# Classes COCO: car=2, motorcycle=3, bus=5, truck=7
TRUCK_CLASS: int = 7

# Calibração: quantos metros correspondem a 1 pixel na cena
# Exemplo: se 270 mm (0.270 m) na pista equivalem a 1024 pixels → 0.270/1024 = 0.0002636 m/px
METERS_PER_PIXEL: float = 0.2858 / 1080.0

# Região de interesse (eixo Y) onde a velocidade é medida
ROI_Y_MIN: int = 200
ROI_Y_MAX: int = 600

# Filtros de detecção
MIN_AREA: int = 400          # área mínima da bbox em pixels²
CONFIDENCE: float = 0.5      # confiança mínima do YOLO

# FPS fixo da câmera — usado no cálculo de velocidade e na captura RTSP
FPS: int = 30

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
PLATE_MODEL_PATH: str = "https://huggingface.co/felipedutrain/placa-br-yolov11/resolve/main/best.pt"

# ── Banco de dados SQLite ─────────────────────────────────────────────────────
DB_PATH: str = "truck_history.db"

# Diretório para salvar snapshots dos caminhões (relativo à raiz do projeto)
SNAPSHOT_DIR: str = "snapshots"

# Identificador da câmera (útil para futuras instalações multi-câmera)
CAMERA_ID: str = "cam01"

# Intervalo de frames para rodar OCR dentro do ROI (throttle — OCR é lento)
PLATE_OCR_INTERVAL: int = 10
