# IA North — Speed Detection Dashboard

## English

### Overview

A real-time truck speed detection system using YOLO11 object detection and centroid tracking. Detects vehicles in video streams (RTSP cameras or MP4 files), measures pixel displacement across frames, and converts to km/h using calibration.

**Features:**
- 🚚 Real-time truck detection and tracking (YOLO11 nano)
- 📊 Live speed calculation with moving average smoothing
- 🎯 ROI-based speed measurement (configurable region)
- 📸 License plate OCR with SQLite persistence
- 🚨 Overspeed alerts with configurable thresholds
- 💾 Historical data logging (truck passages, speeds, plates)
- 🌐 Web dashboard with WebSocket live updates
- 🖥️ FastAPI backend + React frontend

### Tech Stack

**Backend:**
- Python 3.10+
- FastAPI (async REST API + WebSocket)
- Ultralytics YOLO11 (object detection)
- TensorRT/CUDA (GPU acceleration, optional)
- OpenCV (video processing)
- SQLite (truck history)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- WebSocket (real-time updates)

### Architecture

```
Video Stream (RTSP/MP4)
         ↓
   RTSPReader (async thread)
         ↓
  SpeedDetector (YOLO inference)
         ↓
  CentroidTracker (frame-to-frame ID matching)
         ↓
  Speed Calculation + OCR + Alerts
         ↓
  WebSocket → Dashboard (Live feed + stats)
```

### Setup & Running

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Configure the RTSP source:**
   Edit `backend/config.py`:
   ```python
   RTSP_URL = "rtsp://admin:password@camera-ip:554/stream"
   ```

3. **Run backend:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

4. **Run frontend (separate terminal):**
   ```bash
   cd frontend && npm run dev
   ```

5. **Access dashboard:**
   Open `http://localhost:5173`

### Configuration

**Key settings** (`backend/config.py`):
| Setting | Purpose | Default |
|---|---|---|
| `RTSP_URL` | Video source | RTSP camera at 10.6.51.206 |
| `MODEL_PATH` | YOLO weights | `yolo11n.engine` (TensorRT) or `yolo11n.pt` |
| `METERS_PER_PIXEL` | Calibration | 0.265 mm/pixel |
| `ROI_Y_MIN / ROI_Y_MAX` | Speed measurement zone | 200–600 pixels |
| `DEFAULT_THRESHOLD_KMH` | Overspeed alert threshold | 80 km/h |
| `FPS` | Fixed frame rate | 30 fps |

### Calibration

To measure speed accurately, calibrate `meters_per_pixel`:

1. Identify two points in the video frame with a **known real-world distance** (e.g., lane markings).
2. Measure their **pixel distance** in the frame.
3. Update via WebSocket API:
   ```json
   { "type": "set_calibration", "meters_per_pixel": 0.000264 }
   ```
   Or use two-point calibration:
   ```json
   {
     "px1": [100, 300],
     "px2": [520, 300],
     "real_meters": 15.0
   }
   ```

### Performance

- **Inference:** ~25 ms/frame (YOLO11n on RTX 4060)
- **FPS:** 30 fps (fixed)
- **Latency:** ~100 ms (capture → detection → display)
- **GPU:** Optional; falls back to CPU if CUDA unavailable

### GPU Acceleration (TensorRT)

For faster inference:
```bash
python export_tensorrt.py
```
This exports `yolo11n.pt` → `yolo11n.engine` (FP16 quantized, ~2x faster).

### API Endpoints

**WebSocket:**
- `/ws` — Live frame stream + stats + truck data

**HTTP:**
- `GET /api/camera-info` — Camera IP and channel
- `GET /api/history?limit=100` — Historical truck passages
- `POST /api/calibrate` — Update calibration (meters_per_pixel)
- `GET /health` — Health check

### Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI app + WebSocket
│   ├── config.py            # Configuration
│   ├── detector.py          # YOLO + tracking logic
│   ├── centroid_tracker.py  # ID tracking
│   ├── passage_tracker.py   # OCR + history
│   ├── database.py          # SQLite schema
│   └── models.py            # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main component
│   │   ├── components/      # React components
│   │   ├── hooks/           # useWebSocket, etc.
│   │   ├── assets/
│   │   │   └── ianorth-logo.svg
│   │   └── types.ts
│   ├── index.html
│   └── vite.config.ts
├── speed_detection_test*.py # Standalone examples
├── export_tensorrt.py       # TensorRT export script
├── requirements.txt
└── README.md
```

### Troubleshooting

**CUDA not available:**
The app auto-detects GPU. If CUDA isn't available, it falls back to CPU inference (slower).

**TensorRT engine not found:**
Set `MODEL_PATH = "yolo11n.pt"` in `config.py`. Run `python export_tensorrt.py` to generate the `.engine` file.

**RTSP stream disconnects:**
The backend auto-reconnects. Check camera network connectivity and credentials.

**High latency:**
- Reduce `FRAME_JPEG_QUALITY` (default 75) to decrease bandwidth.
- Lower `imgsz` in detector (currently 640) for faster inference.

### License

Internal use — IA North

---

## Português

### Visão Geral

Sistema de detecção de velocidade de caminhões em tempo real usando YOLO11 e rastreamento de centróides. Detecta veículos em streams de vídeo (câmeras RTSP ou arquivos MP4), mede deslocamento de pixels entre frames e converte para km/h usando calibração.

**Funcionalidades:**
- 🚚 Detecção e rastreamento de caminhões em tempo real (YOLO11 nano)
- 📊 Cálculo de velocidade ao vivo com suavização de média móvel
- 🎯 Medição de velocidade por zona ROI (região configurável)
- 📸 OCR de placas com persistência em SQLite
- 🚨 Alertas de excesso de velocidade com limites configuráveis
- 💾 Log histórico (passagens, velocidades, placas)
- 🌐 Dashboard web com atualizações em WebSocket
- 🖥️ Backend FastAPI + Frontend React

### Stack Tecnológico

**Backend:**
- Python 3.10+
- FastAPI (REST API assíncrona + WebSocket)
- Ultralytics YOLO11 (detecção de objetos)
- TensorRT/CUDA (aceleração GPU, opcional)
- OpenCV (processamento de vídeo)
- SQLite (histórico de caminhões)

**Frontend:**
- React 18 + TypeScript
- Vite (ferramenta de build)
- Tailwind CSS (estilização)
- WebSocket (atualizações em tempo real)

### Arquitetura

```
Stream de Vídeo (RTSP/MP4)
         ↓
   RTSPReader (thread assíncrona)
         ↓
  SpeedDetector (inferência YOLO)
         ↓
  CentroidTracker (rastreamento de IDs)
         ↓
  Cálculo de Velocidade + OCR + Alertas
         ↓
  WebSocket → Dashboard (stream ao vivo + stats)
```

### Setup e Execução

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Configurar fonte RTSP:**
   Editar `backend/config.py`:
   ```python
   RTSP_URL = "rtsp://admin:senha@ip-camera:554/stream"
   ```

3. **Executar backend:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

4. **Executar frontend (outro terminal):**
   ```bash
   cd frontend && npm run dev
   ```

5. **Acessar dashboard:**
   Abrir `http://localhost:5173`

### Configuração

**Parâmetros principais** (`backend/config.py`):
| Parâmetro | Propósito | Padrão |
|---|---|---|
| `RTSP_URL` | Fonte de vídeo | Câmera RTSP em 10.6.51.206 |
| `MODEL_PATH` | Pesos YOLO | `yolo11n.engine` (TensorRT) ou `yolo11n.pt` |
| `METERS_PER_PIXEL` | Calibração | 0.265 mm/pixel |
| `ROI_Y_MIN / ROI_Y_MAX` | Zona de medição | 200–600 pixels |
| `DEFAULT_THRESHOLD_KMH` | Limite de alerta | 80 km/h |
| `FPS` | Taxa de frames | 30 fps |

### Calibração

Para medir velocidade com precisão, calibre `meters_per_pixel`:

1. Identifique dois pontos no frame com **distância real conhecida** (ex: marcações de pista).
2. Meça sua **distância em pixels** no frame.
3. Atualize via WebSocket:
   ```json
   { "type": "set_calibration", "meters_per_pixel": 0.000264 }
   ```
   Ou use calibração de dois pontos:
   ```json
   {
     "px1": [100, 300],
     "px2": [520, 300],
     "real_meters": 15.0
   }
   ```

### Performance

- **Inferência:** ~25 ms/frame (YOLO11n em RTX 4060)
- **FPS:** 30 fps (fixo)
- **Latência:** ~100 ms (captura → detecção → exibição)
- **GPU:** Opcional; fallback para CPU se CUDA indisponível

### Aceleração GPU (TensorRT)

Para inferência mais rápida:
```bash
python export_tensorrt.py
```
Exporta `yolo11n.pt` → `yolo11n.engine` (quantizado FP16, ~2x mais rápido).

### Endpoints da API

**WebSocket:**
- `/ws` — Stream ao vivo + stats + dados de caminhões

**HTTP:**
- `GET /api/camera-info` — IP e canal da câmera
- `GET /api/history?limit=100` — Histórico de passagens
- `POST /api/calibrate` — Atualizar calibração (meters_per_pixel)
- `GET /health` — Health check

### Estrutura do Projeto

```
.
├── backend/
│   ├── main.py              # App FastAPI + WebSocket
│   ├── config.py            # Configuração
│   ├── detector.py          # YOLO + lógica de rastreamento
│   ├── centroid_tracker.py  # Rastreamento de IDs
│   ├── passage_tracker.py   # OCR + histórico
│   ├── database.py          # Schema SQLite
│   └── models.py            # Modelos Pydantic
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Componente principal
│   │   ├── components/      # Componentes React
│   │   ├── hooks/           # useWebSocket, etc.
│   │   ├── assets/
│   │   │   └── ianorth-logo.svg
│   │   └── types.ts
│   ├── index.html
│   └── vite.config.ts
├── speed_detection_test*.py # Exemplos standalone
├── export_tensorrt.py       # Script de export TensorRT
├── requirements.txt
└── README.md
```

### Solução de Problemas

**CUDA não disponível:**
A app detecta GPU automaticamente. Se CUDA não estiver disponível, recai para CPU (mais lento).

**Engine TensorRT não encontrado:**
Configure `MODEL_PATH = "yolo11n.pt"` em `config.py`. Execute `python export_tensorrt.py` para gerar o arquivo `.engine`.

**Stream RTSP desconecta:**
O backend reconecta automaticamente. Verifique conectividade de rede e credenciais da câmera.

**Latência alta:**
- Reduza `FRAME_JPEG_QUALITY` (padrão 75) para diminuir banda.
- Abaixe `imgsz` no detector (atualmente 640) para inferência mais rápida.

### Licença

Uso interno — IA North
