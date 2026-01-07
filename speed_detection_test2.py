import cv2  # OpenCV - biblioteca para processar vídeos/imagens
import time  # mede tempo entre frames
import math  # calcula a distância
from ultralytics import YOLO  # modelo de IA para detectar objetos
from collections import OrderedDict  # dicionário que memoriza a ordem de inserção
import numpy as np  # operações numéricas com arrays e matrizes, usada para Álgebra Linear, Transformatas de Fourier, etc.

# 2º Passo: Implementar uma classe que servirá de rastreador de centróides estático
class CentroidTracker:
    def __init__(self, max_disappeared=30): # Método construtor da classe CentroidTracker
        self.next_object_id = 0 # ID do próximo objeto a ser registrado
        self.objects = OrderedDict()      # guarda os objetos rastreados: id -> (cx, cy)
        self.disappeared = OrderedDict()  # guarda o número de frames que cada objeto desapareceu: id -> frames disappeared
        self.max_disappeared = max_disappeared # número máximo de frames que um objeto pode desaparecer antes de ser removido

    def register(self, centroid): # Método para registrar um novo objeto
        self.objects[self.next_object_id] = centroid # adiciona o centróide ao dicionário de objetos
        self.disappeared[self.next_object_id] = 0 # inicializa o contador de desaparecimento para esse objeto
        self.next_object_id += 1 # incrementa o ID para o próximo objeto

    def deregister(self, object_id): # Método para remover um objeto que desapareceu
        if object_id in self.objects: # verifica se o objeto existe
            del self.objects[object_id] # remove o objeto do dicionário de objetos
        if object_id in self.disappeared: # verifica se o objeto existe no dicionário de desaparecidos
            del self.disappeared[object_id] # remove o objeto do dicionário de desaparecidos

    def update(self, input_centroids): # Método para atualizar os objetos rastreados com novos centróides
         # converte os centróides de entrada para tuplas de inteiros
        input_centroids = [tuple(map(int, c)) for c in input_centroids]

        if len(input_centroids) == 0: # se não há centróides de entrada
            for object_id in list(self.disappeared.keys()): # itera sobre os objetos rastreados
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared: # se o objeto desapareceu por mais do que o permitido
                    self.deregister(object_id) # remove o objeto
            return self.objects # retorna os objetos rastreados

        if len(self.objects) == 0: # se não há objetos rastreados
            for c in input_centroids: # registra todos os centróides de entrada
                self.register(c)
            return self.objects

        object_ids = list(self.objects.keys()) # lista de IDs dos objetos rastreados
        object_centroids = np.array(list(self.objects.values()), dtype="int32") # array dos centróides dos objetos rastreados
        input_centroids_arr = np.array(input_centroids, dtype="int32") # array dos centróides de entrada

        D = np.linalg.norm(
            np.expand_dims(object_centroids, axis=1) -
            np.expand_dims(input_centroids_arr, axis=0),
            axis=2
        ) # matriz de distâncias entre centróides rastreados e de entrada

        rows = D.min(axis=1).argsort() # ordena as linhas pela distância mínima
        cols = D.argmin(axis=1)[rows] # obtém os índices das colunas correspondentes

        used_rows = set() # conjunto de linhas já usadas
        used_cols = set() # conjunto de colunas já usadas

        for (row, col) in zip(rows, cols): # itera sobre as correspondências
            if row in used_rows or col in used_cols:  # se a linha ou coluna já foi usada, pula
                continue
            object_id = object_ids[row] # obtém o ID do objeto correspondente
            self.objects[object_id] = tuple(input_centroids[col]) # atualiza o centróide do objeto
            self.disappeared[object_id] = 0 # reseta o contador de desaparecimento
            used_rows.add(row) # marca a linha como usada
            used_cols.add(col) # marca a coluna como usada

        unused_rows = set(range(0, D.shape[0])).difference(used_rows) # linhas não usadas
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        unused_cols = set(range(0, len(input_centroids))).difference(used_cols) # colunas não usadas
        for col in unused_cols:
            self.register(input_centroids[col])

        return self.objects

# 3º Passo: Configurações
RTSP_URL = "rtsp://admin:eletricasnb2021@10.6.51.220:554/cam/realmonitor?channel=1&subtype=1"
MODEL_PATH = "yolov8n.pt"  # arquivo do modelo YOLOv8 pré-treinado
METERS_PER_PIXEL = 10.0 / 200.0  # calibra a cena 1 pixel = 0.05 metros (ajustar)
ROI_Y_MIN, ROI_Y_MAX = 300, 600  # região de interesse (em y) para medir velocidade
MIN_AREA = 400  # filtro por área mínima da bbox
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO dataset: car, motorcycle, bus, truck

# 4º Passo: Captura de vídeo e inicialização do modelo e rastreador
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
if not cap.isOpened():
    cap = cv2.VideoCapture(RTSP_URL)  # fallback

model = YOLO(MODEL_PATH)
ct = CentroidTracker(max_disappeared=20)

last_pos = {}   # track_id -> (cx, cy, frame_idx)
frame_idx = 0
last_time = time.time()
fps = 30.0

# 5º Passo: Loop principal de processamento de vídeo
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

    # Detectação de veículos e extração de bboxes
    # inferência → Pega o frame, redimensiona para 640x640, e aplica confiança mínima de 0.35
    results = model(frame, imgsz=640, conf=0.35)[0]

    # Extrai bboxes e centroides
    boxes = results.boxes
    rects = []
    centroids = []

    # Filtra bboxes detectadas
    if boxes is not None and len(boxes) > 0:
        xyxy = boxes.xyxy.cpu().numpy()  # (N,4)
        cls = boxes.cls.cpu().numpy().astype(int)
        # filtra por classes de veículo e área mínima
        for box, c in zip(xyxy, cls):
            if int(c) not in VEHICLE_CLASSES:
                continue # filtra só veículos
            x1, y1, x2, y2 = box # coordenadas da bbox
            w = x2 - x1
            h = y2 - y1
            area = w * h
            if area < MIN_AREA: # filtra por área mínima
                continue
            cx = int((x1 + x2) / 2) # centróide x
            cy = int(y2)  # centróide y (base da bbox)
            rects.append((int(x1), int(y1), int(x2), int(y2))) # armazena bbox
            centroids.append((cx, cy)) # armazena centróide

    objects = ct.update(centroids) # atualiza rastreador com novos centroides

    annotated = frame.copy() # cópia do frame para anotações

    # 6º Passo: Calcula velocidade para cada objeto rastreado
    for object_id, centroid in objects.items(): # itera sobre os objetos rastreados
        cx, cy = centroid # obtém centróide
        speed_kmh = 0.0 # inicializa velocidade
        # encontrar bbox mais próxima do centróide atual
        best_idx = None # índice da melhor bbox
        best_dist = float("inf") # distância inicial infinita
        for i, c in enumerate(centroids): # itera sobre os centroides detectados
            d = math.hypot(cx - c[0], cy - c[1]) # calcula distância euclidiana
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx is not None and best_idx < len(rects): # se encontrou uma bbox correspondente
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

    # 7º Passo: Exibe o frame anotado
    cv2.imshow("speed estimation", annotated)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")): # 27=ESC
        break

cap.release()
cv2.destroyAllWindows()