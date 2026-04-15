import cv2
import math
from ultralytics import YOLO
from collections import OrderedDict
import numpy as np


class CentroidTracker:
    def __init__(self, max_disappeared=30):
        self.next_object_id = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.max_disappeared = max_disappeared

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id):
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]

    def update(self, input_centroids):
        input_centroids = [tuple(map(int, c)) for c in input_centroids]

        if len(input_centroids) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        if len(self.objects) == 0:
            for c in input_centroids:
                self.register(c)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = np.array(list(self.objects.values()), dtype="int32")
        input_centroids_arr = np.array(input_centroids, dtype="int32")

        D = np.linalg.norm(
            np.expand_dims(object_centroids, axis=1) -
            np.expand_dims(input_centroids_arr, axis=0),
            axis=2
        )

        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for (row, col) in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            object_id = object_ids[row]
            self.objects[object_id] = tuple(input_centroids[col])
            self.disappeared[object_id] = 0
            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(0, D.shape[0])).difference(used_rows)
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        unused_cols = set(range(0, len(input_centroids))).difference(used_cols)
        for col in unused_cols:
            self.register(input_centroids[col])

        return self.objects


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

# 🎬 CAMINHO DO VÍDEO MP4
VIDEO_PATH = "demo/highway.mp4"

# 🧠 MODELO YOLO
MODEL_PATH = "yolo11n.pt"  # baixa automaticamente se não existir

# 📏 CALIBRAÇÃO (ajustar)
METERS_PER_PIXEL = 10.0 / 200.0  # exemplo: 10 metros = 200 pixels

# 🎯 REGIÃO DE INTERESSE (ROI) - ajustar
ROI_Y_MIN, ROI_Y_MAX = 300, 600  # faixa vertical onde medir velocidade

# 🔧 PARÂMETROS DE DETECÇÃO
MIN_AREA = 400  # área mínima da bbox (filtra ruídos)
CONFIDENCE = 0.35  # confiança mínima do YOLO (0.0 a 1.0)
VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck (COCO)

# 💾 SALVAR VÍDEO PROCESSADO?
SAVE_OUTPUT = True  # True para salvar, False para só visualizar
OUTPUT_PATH = "output_velocidades.mp4"

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

print("🎬 Abrindo vídeo...")
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"❌ ERRO: Não consegui abrir o vídeo '{VIDEO_PATH}'")
    print("Verifique se:")
    print("  1. O caminho está correto")
    print("  2. O arquivo existe")
    print("  3. O formato é suportado (mp4, avi, mov, etc)")
    exit()

# Pega informações do vídeo
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or fps is None:
    fps = 30.0
    print("⚠️ Não consegui detectar FPS, usando 30 FPS como padrão")

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"✅ Vídeo carregado:")
print(f"   Resolução: {width}x{height}")
print(f"   FPS: {fps:.2f}")
print(f"   Total frames: {total_frames}")
print(f"   Duração: {total_frames / fps:.2f} segundos")
print()

# Inicializa YOLO
print("🧠 Carregando modelo YOLO...")
model = YOLO(MODEL_PATH)
print("✅ Modelo carregado!")
print()

# Inicializa tracker
ct = CentroidTracker(max_disappeared=20)

# Prepara gravação de vídeo (se habilitado)
out = None
if SAVE_OUTPUT:
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))
    print(f"💾 Vídeo processado será salvo em: {OUTPUT_PATH}")
    print()

# Variáveis de controle
last_pos = {}
frame_idx = 0

print("🚀 Processando vídeo...")
print("Pressione 'Q' ou 'ESC' para parar")
print("-" * 60)

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

while True:
    ret, frame = cap.read()
    if not ret:
        print("\n✅ Processamento concluído!")
        break

    frame_idx += 1

    # Barra de progresso
    if frame_idx % 30 == 0:  # atualiza a cada 30 frames
        progress = (frame_idx / total_frames) * 100
        print(f"Progresso: {progress:.1f}% ({frame_idx}/{total_frames})", end='\r')

    # Detecção YOLO
    results = model(frame, imgsz=640, conf=CONFIDENCE, verbose=False)[0]

    boxes = results.boxes
    rects = []
    centroids = []

    # Processa detecções
    if boxes is not None and len(boxes) > 0:
        xyxy = boxes.xyxy.cpu().numpy()
        cls = boxes.cls.cpu().numpy().astype(int)

        for box, c in zip(xyxy, cls):
            if int(c) not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = box
            w = x2 - x1
            h = y2 - y1
            area = w * h

            if area < MIN_AREA:
                continue

            cx = int((x1 + x2) / 2)
            cy = int(y2)  # base da bbox
            rects.append((int(x1), int(y1), int(x2), int(y2)))
            centroids.append((cx, cy))

    # Atualiza rastreamento
    objects = ct.update(centroids)

    # Cria frame anotado
    annotated = frame.copy()

    # Processa cada objeto rastreado
    for object_id, centroid in objects.items():
        cx, cy = centroid
        speed_kmh = 0.0

        # Encontra bbox correspondente
        best_idx = None
        best_dist = float("inf")
        for i, c in enumerate(centroids):
            d = math.hypot(cx - c[0], cy - c[1])
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx is not None and best_idx < len(rects):
            x1, y1, x2, y2 = rects[best_idx]

            # Calcula velocidade se dentro do ROI
            if ROI_Y_MIN <= cy <= ROI_Y_MAX:
                if object_id in last_pos:
                    last_cx, last_cy, last_f = last_pos[object_id]
                    df = frame_idx - last_f
                    if df > 0:
                        dpx = math.hypot(cx - last_cx, cy - last_cy)
                        dt = df / fps
                        dm = dpx * METERS_PER_PIXEL
                        v_ms = dm / dt if dt > 0 else 0.0
                        speed_kmh = v_ms * 3.6

                last_pos[object_id] = (cx, cy, frame_idx)

            # Desenha bbox e informações
            color = (0, 255, 0) if speed_kmh < 60 else (0, 165, 255) if speed_kmh < 80 else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label = f"ID:{object_id} {speed_kmh:4.1f} km/h"
            cv2.putText(annotated, label, (x1, max(y1 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.circle(annotated, (cx, cy), 4, color, -1)

    # Desenha ROI
    cv2.rectangle(annotated, (0, ROI_Y_MIN), (width, ROI_Y_MAX), (255, 0, 0), 2)
    cv2.putText(annotated, "ROI (Zona de Medicao)", (10, ROI_Y_MIN - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Informações na tela
    cv2.putText(annotated, f"FPS: {fps:.1f} | Frame: {frame_idx}/{total_frames}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Salva frame processado
    if SAVE_OUTPUT and out is not None:
        out.write(annotated)

    # Mostra resultado
    cv2.imshow("Medicao de Velocidade - MP4", annotated)

    # Controles
    key = cv2.waitKey(1) & 0xFF
    if key in (27, ord('q'), ord('Q')):  # ESC ou Q
        print("\n⏸️ Processamento interrompido pelo usuário")
        break

# =============================================================================
# FINALIZAÇÃO
# =============================================================================

cap.release()
if out is not None:
    out.release()
cv2.destroyAllWindows()

print("-" * 60)
print("🏁 FINALIZADO!")