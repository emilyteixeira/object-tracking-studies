import cv2
import time
import math
from ultralytics import YOLO
from collections import OrderedDict
import numpy as np

class CentroidTracker:
    def __init__(self, max_disappeared=30):
        self.next_object_id = 0
        self.objects = OrderedDict()      # id -> (cx, cy)
        self.disappeared = OrderedDict()  # id -> frames disappeared
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

# --- Configurações ---
RTSP_URL = "rtsp://admin:eletricasnb2021@10.6.51.220:554/cam/realmonitor?channel=1&subtype=1"
MODEL_PATH = "yolov8n.pt"  # ajuste conforme / ou deixe "yolov8n.pt"
METERS_PER_PIXEL = 10.0 / 200.0  # calibrar para sua cena
ROI_Y_MIN, ROI_Y_MAX = 300, 600  # banda ROI (ajuste)
MIN_AREA = 400  # filtro por área mínima da bbox
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO: car, motorcycle, bus, truck

# --- Inicialização ---
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
if not cap.isOpened():
    cap = cv2.VideoCapture(RTSP_URL)  # fallback

model = YOLO(MODEL_PATH)
ct = CentroidTracker(max_disappeared=20)

last_pos = {}   # track_id -> (cx, cy, frame_idx)
frame_idx = 0
last_time = time.time()
fps = 30.0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1

    # calcula fps em tempo real
    now = time.time()
    dt_frame = now - last_time if (now - last_time) > 1e-6 else 1e-6
    fps = 1.0 / dt_frame
    last_time = now

    # inferência (retorna lista; pegamos [0])
    results = model(frame, imgsz=640, conf=0.35)[0]

    boxes = results.boxes  # ultralytics Boxes object
    rects = []
    centroids = []

    if boxes is not None and len(boxes) > 0:
        xyxy = boxes.xyxy.cpu().numpy()  # (N,4)
        cls = boxes.cls.cpu().numpy().astype(int)
        # filtra por classes de veículo e área mínima
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
            cy = int(y2)  # ponto de contato na estrada (inferência)
            rects.append((int(x1), int(y1), int(x2), int(y2)))
            centroids.append((cx, cy))

    objects = ct.update(centroids)

    annotated = frame.copy()

    # para cada objeto rastreado, achar bbox correspondente (melhor match por distância)
    for object_id, centroid in objects.items():
        cx, cy = centroid
        speed_kmh = 0.0
        # encontrar bbox mais próxima do centróide atual
        best_idx = None
        best_dist = float("inf")
        for i, c in enumerate(centroids):
            d = math.hypot(cx - c[0], cy - c[1])
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx is not None and best_idx < len(rects):
            x1, y1, x2, y2 = rects[best_idx]
            # só medir se dentro do ROI
            if ROI_Y_MIN <= cy <= ROI_Y_MAX:
                if object_id in last_pos:
                    last_cx, last_cy, last_f = last_pos[object_id]
                    df = frame_idx - last_f
                    if df > 0:
                        dpx = math.hypot(cx - last_cx, cy - last_cy)
                        dt = df / max(fps, 1e-6)
                        dm = dpx * METERS_PER_PIXEL
                        v_ms = dm / dt if dt > 0 else 0.0
                        speed_kmh = v_ms * 3.6
                # atualizar posição
                last_pos[object_id] = (cx, cy, frame_idx)

            # desenha bbox e label
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"ID {object_id} {speed_kmh:4.1f} km/h"
            cv2.putText(annotated, label, (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.circle(annotated, (cx, cy), 4, (0, 255, 0), -1)

    # desenha ROI
    cv2.rectangle(annotated, (0, ROI_Y_MIN), (annotated.shape[1], ROI_Y_MAX), (255, 0, 0), 2)
    cv2.putText(annotated, f"FPS: {fps:4.1f}", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("speed estimation", annotated)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

cap.release()
cv2.destroyAllWindows()