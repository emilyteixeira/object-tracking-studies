from idlelib.format import Rstrip

import cv2
import numpy as np
from collections import OrderedDict
from ultralytics import YOLO
from scipy.spatial import distance as dist
import torch
import math
import time

# ---------- Simple Centroid Tracker ----------

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
        del self.objects[object_id]
        del self.disappeared[object_id]

    def update(self, input_centroids):
        # no detections: mark existing as disappeared
        if len(input_centroids) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        # first frame: register all
        if len(self.objects) == 0:
            for c in input_centroids:
                self.register(c)
            return self.objects

        # match input centroids to existing objects by nearest neighbor
        object_ids = list(self.objects.keys())
        object_centroids = list(self.objects.values())

        D = np.linalg.norm(
            np.expand_dims(object_centroids, axis=1) -
            np.expand_dims(input_centroids, axis=0),
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
            self.objects[object_id] = input_centroids[col]
            self.disappeared[object_id] = 0
            used_rows.add(row)
            used_cols.add(col)

        # unassigned existing objects
        unused_rows = set(range(0, D.shape[0])).difference(used_rows)
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        # new objects
        unused_cols = set(range(0, len(input_centroids))).difference(used_cols)
        for col in unused_cols:
            self.register(input_centroids[col])

        return self.objects

# ---------- Main: detection + speed ----------

RTSP_URL = "rtsp://admin:eletricasnb2021@10.6.58.207:554/cam/realmonitor?channel=1&subtype=1"
cap = cv2.VideoCapture(
    RTSP_URL,
    cv2.CAP_FFMPEG
)

cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

fps = cap.get(cv2.CAP_PROP_FPS)
prev_time = time.time()
fps = 0.0

current_time = time.time()
fps = 1 / (current_time - prev_time)
prev_time = current_time

# Detection Model (YOLO on PyTorch)
device = "cuda" if torch.cuda.is_available() else "cpu"

model = YOLO("yolov8n.pt").to(device)

VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck

# Tracking (with ByteTrack built-in)
results = model.track(source=RTSP_URL, persist=True, tracker="bytetrack.yaml", device=device, stream=True)

# Defining a measurement line (more friendly)
# for 720p frame:
line1_y = 520 # line 1 position in pixels
line2_y = 440 # line 2 position in pixels

# Knowing the real distance between two lines in the scene to estimate speed
distance_meters = 10.0  # real distance in meters between two lines

# Measuring the pixel distance between the two lines in the image
# (it must be measured manually on a sample frame)
pixel_distance = abs(line2_y - line1_y)# example value

# meters per pixel (you must calibrate this!)
# example: 10 meters on road correspond to 200 pixels in image -> 10 / 200
meters_per_pixel = distance_meters / pixel_distance

# Robust Speed Estimation Logic
vehicle_times = {}
vehicle_positions = {}
frame_count = 0
crossed_line_A = False
crossed_line_B = False
t1 = int
t2 = int

for track in results[0].boxes:
    track_id = int(track.id)
    x1, y1, x2, y2 = track.xyxy[0]
    center_y = int((y1 + y2) / 2)

    if track_id not in vehicle_positions:
        vehicle_positions[track_id] = []

    vehicle_positions[track_id].append(frame_count, center_y)

    # Detect crossing
    if crossed_line_A:
        vehicle_times[track_id][t1] = frame_count
    if crossed_line_B:
        vehicle_times[track_id][t2] = frame_count

# Speed calculation
time_sec = [(t2 - t1) / fps]
speed_m_s = distance_meters / time_sec
speed_kmh = speed_m_s * 3.6

# Robust Speed Estimation Logic (Alternative using Background Subtraction + Centroid Tracking)
bg_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

ct = CentroidTracker(max_disappeared=15)

# store last position & frame for each id
last_position = {}  # id -> (cx, cy, frame_idx)

frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    h, w = frame.shape[:2]

    # --- background subtraction ---
    fgmask = bg_sub.apply(frame)
    fgmask = cv2.GaussianBlur(fgmask, (5, 5), 0)
    _, fgmask = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    fgmask = cv2.dilate(fgmask, None, iterations=2)

    contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    centroids = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < 500:  # ignore noise
            continue
        x, y, w_box, h_box = cv2.boundingRect(c)
        rects.append((x, y, w_box, h_box))
        cx = int(x + w_box / 2)
        cy = int(y + h_box / 2)
        centroids.append((cx, cy))

    objects = ct.update(centroids)

    for object_id, (cx, cy) in objects.items():
        # draw bbox if available
        # (optional) find corresponding rect again to draw
        # here just draw the point
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        # compute speed
        speed_kmh = 0.0
        if object_id in last_position:
            last_cx, last_cy, last_f = last_position[object_id]
            df = frame_idx - last_f
            if df > 0:
                dpx = math.hypot(cx - last_cx, cy - last_cy)
                dt = df / fps
                dm = dpx * meters_per_pixel
                v_ms = dm / dt if dt > 0 else 0.0
                speed_kmh = v_ms * 3.6

        # update history
        last_position[object_id] = (cx, cy, frame_idx)

        # draw ID and speed
        text = f"ID {object_id} | {speed_kmh:5.1f} km/h"
        cv2.putText(frame, text, (cx + 10, cy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    cv2.imshow("frame", frame)
    cv2.imshow("fgmask", fgmask)

    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord('q'):
        break

# Checking for GPU
if torch.cuda.is_available and torch.cuda.device_name(0):
    print("Using GPU:", torch.cuda.device_name(0))
    print("GPU Details:")
    print(torch.cuda.get_device_properties(0))

    model = YOLO("yolov8n.pt")
    model.fuse()

    results = model.track(
        source = RTSP_URL,
        stream=True,
        half=True,
        device=0,
        persist=True,
        tracker="bytetrack.yaml"
    )
else:
    print("Using CPU")

cap.release()
cv2.destroyAllWindows()
