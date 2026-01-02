# Object Tracking and Speed Detection with OpenCV and Python3

You can implement object tracking and speed estimation in Python with OpenCV by combining a lightweight tracker (e.g., centroid/tracker or MOSSE/CSRT) with a simple speed calculation using frame-to-frame centroids and a known frame rate or perspective-based calibration.

### What to cover
- Core approaches
- Minimal working workflow
- Speed estimation options and calibration tips
- Example starter code structure
- Common pitfalls and debugging tips

### Core approaches
- Object tracking methods:
  - Centroid tracking: assign IDs to detected objects and update positions by nearest centroid in subsequent frames.
  - More advanced trackers: CSRT, KCF, MOSSE, or Deep SORT for robust re-identification across frames.
- Speed estimation strategies:
  - Planar speed from pixel distance: speed ≈ (distance in pixels) × scale_factor / time_between_frames.
  - Calibrated speed using perspective mapping: map pixel coordinates to real-world coordinates via a homography or camera calibration, then compute speed in real units (e.g., m/s).

### Minimal working workflow
- Capture video frames with OpenCV.
- Detect objects of interest (cars, people, etc.). You can start with simple color/shape filters or integrate a DL detector (e.g., YOLO, SSD) if available.
- Initialize a tracker with detected bounding boxes. Assign persistent IDs to each object.
- For each new frame:
  - Update tracker, obtain new centroids and bounding boxes.
  - Compute object speed using the chosen method.
  - Optionally display bounding boxes, IDs, and speed on the frame.
- Repeat until video ends; save results as needed.

### Starter code structure (high-level)
- Import libraries: cv2, numpy
- Initialize video capture and writer (if saving)
- Detect objects in the first frame and create trackers/IDs
- Loop over frames:
  - Read frame
  - If using a detector: run detector every N frames or with a motion-based region proposal
  - Update tracker to get current centers and IDs
  - Compute speed:
    - If using pixel-based: speed_px_per_sec = delta_pixels / delta_time; speed = speed_px_per_sec × pixels_to_meters
    - If using calibration: transform points to real-world coordinates and compute distance/time
  - Draw annotations and show frame
- Release resources

### Practical tips
- Frame rate matters: know the capture FPS precisely to convert pixel movement to speed.
- Calibration improves accuracy: use a known distance in the scene (e.g., lane markings) to estimate a scale factor or compute a homography for real-world mapping.
- Handling occlusions:
  - Use a robust tracker (CSRT or Deep SORT) if objects frequently occlude or cross paths.
  - Maintain IDs across frames and re-identify after misses using appearance features if possible.
- Performance:
  - Start with a lightweight approach (centroid tracker + simple detector) to validate the pipeline.
  - If performance is insufficient, switch to a hardware-accelerated backend or a more efficient detector.

### Common pitfalls
- Incorrect FPS leads to wrong speed estimates.
- Perspective effects cause speed to appear higher/lower depending on distance to the camera.
- Bounding box jitter can break ID continuity; apply smoothing to centroids or use a more robust tracker.

### Recommended next steps
- If you want, I can tailor a compact, ready-to-run Python script using OpenCV that:
  - Detects moving objects with a simple background subtractor
  - Tracks them with a centroid-based ID system
  - Estimates speed with a user-provided scale (meters per pixel) or a basic camera calibration step
- I can also provide a small guide to calibrating a camera for speed estimation in a real scene.

## Next Steps...
A practical way to start is: detect moving objects with background subtraction, track them by centroid with unique IDs, and compute speed from centroid displacement using the video FPS and a pixels→meters scale factor.[1][2]

### Pipeline overview

- Use OpenCV to:
  - Read the video/webcam stream and get its FPS (for \(\Delta t\)).[1]
  - Apply a background subtractor (e.g., MOG2) to get moving blobs.[2][3]
  - Find contours, filter by area, and build bounding boxes.  
- Track:
  - Compute the centroid of each bounding box and feed into a centroid tracker that assigns IDs and keeps history.[4][2]
- Speed:
  - For each ID, store previous centroid and frame index.
  - Distance in pixels: \(d_{px} = \sqrt{\Delta x^2 + \Delta y^2}\).  
  - Time: \(dt = \frac{\Delta \text{frames}}{\text{FPS}}\).[1]
  - Convert to meters: \(d_m = d_{px} \times \text{meters\_per\_pixel}\).[5][1]
  - Speed in km/h: \(v = \frac{d_m}{dt} \times 3.6\).  

### Minimal example (single file)

This is a compact, didactic script using background subtraction + centroid tracking + simple pixel→meter scale. Adjust comments and structure as you like for teaching.

```python
import cv2
import numpy as np
from collections import OrderedDict
import math

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

video_path = "video.mp4"  # or 0 for webcam
cap = cv2.VideoCapture(video_path)

fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0:
    fps = 30.0  # fallback

# meters per pixel (you must calibrate this!)
# example: 10 meters on road correspond to 200 pixels in image -> 10 / 200
METERS_PER_PIXEL = 10.0 / 200.0

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
                dm = dpx * METERS_PER_PIXEL
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

cap.release()
cv2.destroyAllWindows()
```

This structure is adapted from common centroid-tracking and background-subtraction examples for OpenCV object tracking and vehicle speed estimation.[6][4][2]

### Calibrating pixels to meters

For a first pass you can use a single linear scale factor:

- Pick two points on the road/floor that are:
  - Aligned with the motion direction.
  - At roughly the same depth (to reduce perspective error).[5][1]
- Measure their distance in the real world (e.g., 10 meters).  
- Measure the distance between the same points in the image (in pixels) using a drawing tool or a quick OpenCV script.  
- Compute \(\text{meters\_per\_pixel} = \frac{\text{real\_distance\_m}}{\text{pixel\_distance}}\).[5][1]
- Replace `METERS_PER_PIXEL` in the script with that value.

For better accuracy with oblique views, you can warp the road region to a top-down view using a perspective transform (homography) and then measure distances in that warped image, as shown in recent speed-estimation tutorials.[7][8][1]

### Where to go deeper

- Detailed centroid tracker implementation and theory: PyImageSearch’s centroid tracking article.[4]
- Full vehicle detection + Deep Learning + speed estimation: OpenCV vehicle speed tutorial.[6]
- Modern multi-object tracking and accuracy considerations (FPS, angle, distortion): recent blog posts and videos on speed estimation with OpenCV.[8][1]

If you tell the target context (traffic, pedestrians, robotics lab, etc.), a more specialized version can be sketched, e.g., with YOLO for detection or with a homography step already set up for classroom demos.

### Fontes
[1] Estimate the speed of any object | with Python and OpenCV https://pysource.com/2025/08/13/estimate-the-speed-of-any-object-with-python-and-opencv/
[2] Object Detection and Tracking with OpenCV background subtractors https://github.com/IvanGael/Object_Detection_With_Background_substractor
[3] Background Subtraction - OpenCV Documentation https://docs.opencv.org/4.x/d8/d38/tutorial_bgsegm_bg_subtraction.html
[4] Simple object tracking with OpenCV https://pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/
[5] Computing real world distance using pixel distance - Stack Overflow https://stackoverflow.com/questions/61252243/computing-real-world-distance-using-pixel-distance
[6] OpenCV Vehicle Detection, Tracking, and Speed Estimation https://pyimagesearch.com/2019/12/02/opencv-vehicle-detection-tracking-and-speed-estimation/
[7] Estimate the speed of any object | with Python and OpenCV https://www.youtube.com/watch?v=x8ckoE5MbwQ
[8] How to Estimate Speed with Computer Vision - Roboflow Blog https://blog.roboflow.com/estimate-speed-computer-vision/
[9] Getting Started With Object Tracking Using OpenCV https://www.geeksforgeeks.org/computer-vision/getting-started-with-object-tracking-using-opencv/
[10] Object Tracking with OpenCV https://articulatedrobotics.xyz/tutorials/mobile-robot/applications/objtrack/
[11] Calculate FPS and Average FPS from live video using OpenCV python https://www.youtube.com/watch?v=3qFe2X9verQ
[12] The Complete Guide to Object Tracking https://learnopencv.com/the-complete-guide-to-object-tracking-in-computer-vision
[13] Centroid Tracking with by using background subtracting in python https://stackoverflow.com/questions/53604513/centroid-tracking-with-by-using-background-subtracting-in-python
[14] Tracking Objects | OpenCV Python Tutorials for Beginners ... https://www.youtube.com/watch?v=1FJWXOO1SRI
[15] Multiple Object Tracking in Realtime https://opencv.org/blog/multiple-object-tracking-in-realtime/
[16] Meanshift and Camshift - OpenCV Documentation https://docs.opencv.org/4.x/d7/d00/tutorial_meanshift.html
[17] Vehicle Speed Estimation with YOLO11 & OpenCV https://www.kaggle.com/code/mateuszk013/vehicle-speed-estimation-with-yolo11-opencv
[18] Simple Motion Detection using Background Subtraction in Python https://www.youtube.com/watch?v=BURNRHK_r9g
[19] [Python + OpenCV] Is it possible to get the speed of an object you're ... https://www.reddit.com/r/learnpython/comments/b5hqpm/python_opencv_is_it_possible_to_get_the_speed_of/
[20] Object Tracking with Opencv and Python https://www.youtube.com/watch?v=O3b8lVF93jU

---
## Applying the Target Context: Vehicle Speed Measurement with YOLOv11 in Python
You can measure vehicle speed in a region of interest (ROI) with YOLOv11 by combining three pieces: YOLO detection, multi-object tracking with IDs, and calibrated distance‑over‑time inside that ROI.[1][2]

### High-level design

- **Detection:**  
  - Use an Ultralytics YOLO11 model (e.g., `yolo11n.pt` or a traffic‑trained variant) to detect vehicles frame by frame.[3][1]
  - Filter classes to vehicles (car, bus, truck, motorcycle, etc.).[4]
- **Tracking with IDs:**  
  - Use YOLO11’s built‑in tracking mode (`yolo track`) or a Python tracker like ByteTrack/BOT-SORT to keep a consistent ID per vehicle across frames.[1][5][6]
- **Speed estimation in ROI:**  
  - Define a polygon or rectangular ROI where you want valid speed readings.  
  - For each tracked ID, store its previous position (e.g., bounding‑box bottom center) and frame index whenever it is inside the ROI.  
  - Convert pixel displacement to real‑world distance using a calibration factor or perspective transform, then compute speed from distance and time.[4][7][8]

### Practical Python outline (YOLO11 + OpenCV)

Using the Ultralytics Python API (YOLO11) and OpenCV:

```python
from ultralytics import YOLO
import cv2
import math

# 1. Load YOLO11 model
model = YOLO("yolo11n.pt")  # choose size as needed

video_path = "traffic.mp4"
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

# 2. Calibration: meters per pixel in ROI (you must set this!)
METERS_PER_PIXEL = 10.0 / 200.0  # example

# 3. Region of interest (simple horizontal band)
ROI_Y_MIN, ROI_Y_MAX = 300, 600  # adjust to your video

# Store last (x, y, frame) for each track ID
last_pos = {}

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1

    # 4. Inference with tracking
    results = model.track(
        frame,
        persist=True,                # keep track history
        classes=[2, 3, 5, 7],        # example: car, motorcycle, bus, truck (COCO IDs)
        verbose=False
    )

    annotated = frame.copy()

    if results and results[0].boxes is not None:
        boxes = results[0].boxes
        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else None
        cls = boxes.cls.cpu().numpy().astype(int)

        for box, track_id, c in zip(xyxy, ids, cls):
            x1, y1, x2, y2 = box
            cx = int((x1 + x2) / 2)
            cy = int(y2)  # use bottom center for road contact point

            # Check ROI
            if not (ROI_Y_MIN <= cy <= ROI_Y_MAX):
                continue

            # Compute speed if previous position exists
            speed_kmh = 0.0
            if track_id in last_pos:
                last_cx, last_cy, last_f = last_pos[track_id]
                df = frame_idx - last_f
                if df > 0:
                    dpx = math.hypot(cx - last_cx, cy - last_cy)
                    dt = df / fps
                    dm = dpx * METERS_PER_PIXEL
                    v_ms = dm / dt if dt > 0 else 0.0
                    speed_kmh = v_ms * 3.6

            # Update history inside ROI
            last_pos[track_id] = (cx, cy, frame_idx)

            # Draw bbox and speed
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            label = f"ID {track_id} {speed_kmh:4.1f} km/h"
            cv2.putText(annotated, label, (int(x1), int(y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Draw ROI
    cv2.rectangle(annotated, (0, ROI_Y_MIN), (annotated.shape[1], ROI_Y_MAX), (255, 0, 0), 2)

    cv2.imshow("speed estimation", annotated)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

cap.release()
cv2.destroyAllWindows()
```

This structure follows the same principles as YOLO11 speed‑estimation examples and Kaggle notebooks using YOLO11 with OpenCV for vehicle speed.[1][2][9]

### ROI and calibration strategy

- **ROI choice:**  
  - Place the ROI where the road is approximately at a single depth (less perspective distortion).  
  - Use the bottom of the bounding box as the contact point to reduce height variance.[4][8]
- **Single scale factor (simple):**  
  - Measure a known distance on the road that lies within the ROI (e.g., lane markings or a measured 10 m segment).[4][7]
  - Measure that same segment in pixels and set `METERS_PER_PIXEL = real_meters / pixel_length`.  
- **Perspective transform (better):**  
  - Select four corner points of a road patch and warp to a top‑down view using a homography; compute distances in the warped image.[4][8]

### Recommended references

- Ultralytics official guide: **“Speed Estimation using Ultralytics YOLO11”**, which shows how to plug speed estimation into YOLO11 tracking in Python.[1][6]
- Kaggle notebook **“Vehicle Speed Estimation with YOLO11 & OpenCV”** for a full working example and ideas on metrics and visualization.[2][9]
- Roboflow and Pysource tutorials for calibration details and error‑reduction tricks (less than ~5% error achievable with good setup).[4][8]

If you share: (1) your camera angle (side, front‑facing, overhead) and (2) whether you can physically measure distances on the road, a more specific homography + ROI calibration recipe can be outlined for your exact setup.

### Fontes
[1] Speed Estimation using Ultralytics YOLO11 https://docs.ultralytics.com/guides/speed-estimation/
[2] Vehicle Speed Estimation with YOLO11 & OpenCV - Kaggle https://www.kaggle.com/code/mateuszk013/vehicle-speed-estimation-with-yolo11-opencv
[3] Ultralytics YOLO11 https://docs.ultralytics.com/models/yolo11/
[4] Estimate the speed of any object | with Python and OpenCV - Pysource https://pysource.com/2025/08/13/estimate-the-speed-of-any-object-with-python-and-opencv/
[5] Better Vehicle Re-Identification With Ultralytics YOLO Models https://www.ultralytics.com/blog/enhancing-vehicle-re-identification-with-ultralytics-yolo-models
[6] Ultralytics YOLO11 Modes https://docs.ultralytics.com/modes/
[7] Computing real world distance using pixel distance - Stack Overflow https://stackoverflow.com/questions/61252243/computing-real-world-distance-using-pixel-distance
[8] How to Estimate Speed with Computer Vision - Roboflow Blog https://blog.roboflow.com/estimate-speed-computer-vision/
[9] Vehicle Speed Estimation with YOLO11 & OpenCV - Kaggle https://www.kaggle.com/code/abhinavrathore/vehicle-speed-estimation-with-yolo11-opencv
[10] Vehicle Detection and Counting using YOLO11 - GitHub https://github.com/SrujanPR/Vehicle-Detection-and-Counter-using-Yolo11
[11] Speed Estimation of ANY Object in Video using Computer Vision ... https://www.youtube.com/watch?v=fiE0s0SuaL8
[12] YOLO11: Automotive Computer Vision Solutions - Ultralytics https://www.ultralytics.com/blog/ultralytics-yolo11-and-computer-vision-for-automotive-solutions
[13] [PDF] Vehicle Speed Estimation Using YOLO, Kalman Filter, and Frame ... https://informatika.stei.itb.ac.id/~rinaldi.munir/TA/Makalah_TA_Asif.pdf
[14] AI-Powered Vehicle Speed Detection with YOLO11, OpenCV, and ... https://www.linkedin.com/posts/firastlili_computervision-yolo11-deeplearning-activity-7381014227047747585-FDRQ
[15] Vehicle Speed Estimation with YOLO11 & OpenCV - Kaggle https://www.kaggle.com/code/mateuszk013/vehicle-speed-estimation-with-yolo11-opencv/data
[16] Raafat-Nagy/Vehicle-Speed-Estimation-and-Counting-YOLO ... https://github.com/Raafat-Nagy/Vehicle-Speed-Estimation-and-Counting-YOLO-Supervision
[17] Vehicle Speed Estimation with YOLO11 & OpenCV - Kaggle https://www.kaggle.com/code/mateuszk013/vehicle-speed-estimation-with-yolo11-opencv/comments
[18] Estimate the speed of any object | with Python and OpenCV - YouTube https://www.youtube.com/watch?v=x8ckoE5MbwQ
[19] How to extract data from YOLO11? · Issue #18591 - GitHub https://github.com/ultralytics/ultralytics/issues/18591
[20] Vehicle Speed Estimation with YOLO11 & OpenCV | Kaggle https://www.kaggle.com/code/abhinavrathore/vehicle-speed-estimation-with-yolo11-opencv/script
[21] Vehicle Speed Estimation using deep learning with OpenCV https://www.jetir.org/view?paper=JETIR2403777

### Another Questions Suggested
- How to calibrate camera for speed estimation in OpenCV?
- Best multi object trackers for vehicle tracking in YOLOv11?
- How to compute real-world distances from pixel coordinates in video?
- How to implement a complete script for vehicle speed detection using YOLOv11 and OpenCV?
---

# References and Further Reading

## Citations
- **OpenCV-based centroid tracking** and **speed estimation** concepts are widely discussed in tutorials and guides for object tracking and speed measurement in video using OpenCV. If you want, I can pull specific tutorials and link them inline.[2][3][9]

## Fontes
[1] Object Tracking and Detection using OpenCV in python https://github.com/ayush-thakur02/object-tracking-opencv
[2] OpenCV Vehicle Detection, Tracking, and Speed Estimation https://pyimagesearch.com/2019/12/02/opencv-vehicle-detection-tracking-and-speed-estimation/
[3] Object tracking from scratch - OpenCV and python https://pysource.com/2021/10/05/object-tracking-from-scratch-opencv-and-python/
[4] Vehicle Speed Detection using OpenCV and Python https://jpinfotech.org/vehicle-speed-detection-using-opencv-and-python/
[5] Object Tracking from scratch with OpenCV and Python https://www.youtube.com/watch?v=GgGro5IV-cs
[6] Object Tracking and speed detection using OpenCV python https://www.youtube.com/watch?v=GEdO68H46GA
[7] Object Tracking with Opencv and Python https://www.youtube.com/watch?v=O3b8lVF93jU
[8] GitHub - noorkhokhar99/Object-Tracking-and-speed-detection-using-OpenCV-python: Object Tracking and speed detection using OpenCV python https://github.com/noorkhokhar99/Object-Tracking-and-speed-detection-using-OpenCV-python
[9] Object Tracking using OpenCV (C++/Python) https://learnopencv.com/object-tracking-using-opencv-cpp-python/
[10] Motion Tracking in opencv python https://stackoverflow.com/questions/48088534/motion-tracking-in-opencv-python

### Videos
- [Object Tracking from scratch with OpenCV and Python](https://www.youtube.com/watch?v=GgGro5IV-cs)
- [Object Tracking and speed detection using OpenCV python](https://www.youtube.com/watch?v=GEdO68H46GA)
- [Object Tracking with Opencv and Python](https://www.youtube.com/watch?v=O3b8lVF93jU)
- [Vehicle Speed Detection using OpenCV and Python](https://jpinfotech.org/vehicle-speed-detection-using-opencv-and-python/)
- [Object tracking from scratch - OpenCV and python](https://pysource.com/2021/10/05/object-tracking-from-scratch-opencv-and-python/)
- [OpenCV Vehicle Detection, Tracking, and Speed Estimation](https://pyimagesearch.com/2019/12/02/opencv-vehicle-detection-tracking-and-speed-estimation/)

### GitHub Repositories
- https://github.com/ayush-thakur02/object-tracking-opencv

- https://github.com/theAIGuysCode/yolov4-deepsort
- https://github.com/MuhammadMoinFaisal/YOLOv8-DeepSORT-Object-Tracking
- https://github.com/LeonLok/Multi-Camera-Live-Object-Tracking
- https://github.com/jingh-ai/ultralytics-YOLO-DeepSort-ByteTrack-PyQt-GUI

    #### Speed Detection using OpenCV and Python
  - https://github.com/anuraggupta29/vehicle-speed-detection
  - https://github.com/nhatanh174/Speed-Estimate
  - https://github.com/carlobrok/speed_tracker

### Another References
- https://learnopencv.com/object-tracking-using-opencv-cpp-python/

---

Estimating vehicle speed in real time with **OpenCV + YOLO** is a classic (and very doable) computer vision pipeline. The key idea is:

> **Detect → Track → Convert pixels to real-world distance → Measure time → Compute speed**

Below is a clean, practical breakdown that actually works in real-world setups.

---

## 1. High-level pipeline

1. **Detect vehicles** in each frame (YOLO)
2. **Track the same vehicle across frames** (DeepSORT / ByteTrack / SORT)
3. **Measure pixel displacement** over time
4. **Convert pixel distance → meters** (camera calibration or homography)
5. **Compute speed** using FPS and time delta

---

## 2. Vehicle detection (YOLO)

Use YOLOv5 / YOLOv8 (recommended: YOLOv8n or YOLOv8s for real time).

Detect only vehicle classes:

* car
* bus
* truck
* motorcycle

Example (YOLOv8):

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model(frame, conf=0.4, classes=[2, 3, 5, 7])  
# COCO: car=2, motorcycle=3, bus=5, truck=7
```

Each detection gives:

* bounding box `(x1, y1, x2, y2)`
* confidence
* class

---

## 3. Tracking (this is critical)

**Detection alone is NOT enough** — you must track vehicles across frames.

Best options:

* **ByteTrack** (fast, accurate, simple)
* **DeepSORT** (more robust, slower)

Tracking gives each vehicle a **unique ID**.

Example logic (conceptual):

```python
track_id → [(frame_id, center_x, center_y)]
```

You’ll store the **center point** of each bounding box per frame.

---

## 4. Measure pixel displacement

For each tracked vehicle:

```python
dx = x_current - x_previous
dy = y_current - y_previous
pixel_distance = sqrt(dx² + dy²)
```

Over multiple frames, accumulate distance for smoother results.

---

## 5. Convert pixels → meters (MOST IMPORTANT PART)

### Option A: Known distance in scene (simplest)

If you know:

* Lane width
* Distance between road markings
* Length of crosswalk

Then:

```text
meters_per_pixel = real_distance_meters / pixel_distance
```

This works best for:

* Fixed camera
* Slightly angled view

---

### Option B: Homography (recommended)

If the road is approximately planar:

1. Select **4 points on the road** in the image
2. Map them to **real-world coordinates (meters)**

```python
H = cv2.findHomography(image_points, world_points)
world_point = cv2.perspectiveTransform(image_point, H)
```

Now movement is measured **directly in meters** — way more accurate.

---

## 6. Speed calculation

Speed formula:

```text
speed = distance / time
```

In code:

```python
time_sec = frame_delta / fps
speed_mps = distance_meters / time_sec
speed_kmh = speed_mps * 3.6
```

For stability:

* Use distance over **N frames**
* Apply a moving average

---

## 7. Practical speed estimation logic

```python
if len(track_history[id]) >= N:
    p1 = track_history[id][-N]
    p2 = track_history[id][-1]

    distance_m = compute_distance(p1, p2)
    time_s = (N / fps)

    speed_kmh = (distance_m / time_s) * 3.6
```

---

## 8. Common mistakes (watch out ⚠️)

* ❌ No camera calibration → wildly wrong speeds
* ❌ Using bounding box corners instead of center
* ❌ Speed from only 2 frames (very noisy)
* ❌ Camera not fixed
* ❌ Ignoring perspective distortion

---

## 9. Expected accuracy

| Setup                 | Accuracy          |
| --------------------- | ----------------- |
| No calibration        | ❌ unusable        |
| Known road distances  | ±10–15%           |
| Homography + tracking | **±5% or better** |
| Professional systems  | ±1–2%             |

---

## 10. Tech stack recommendation (real-time)

* **YOLOv8n** (detection)
* **ByteTrack** (tracking)
* **OpenCV** (geometry + visualization)
* **FPS ≥ 25** (important for speed stability)

---
