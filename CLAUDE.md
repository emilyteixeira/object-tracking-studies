# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vehicle speed detection system using computer vision. Detects and tracks vehicles in video streams (RTSP cameras or local MP4 files), measures pixel displacement across frames, and converts to km/h using a calibration factor.

## Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the most complete implementation (supports MP4 and RTSP)
python speed_detection_test3.py

# Run the RTSP-only production version
python speed_detection_test2.py
```

**Video input:** Edit the `VIDEO_SOURCE` variable at the top of each script. Set to a local file path (e.g., `demo/highway.mp4`) or an RTSP URL. For webcam use `0`.

**YOLO model:** Scripts auto-download `yolo11n.pt` (nano) on first run via `ultralytics`.

## Architecture

**Pipeline:** Frame capture → YOLO detection → class filtering → centroid tracking → speed calculation → annotated display/output

### CentroidTracker (core class, duplicated across scripts)
Maintains object identity across frames using nearest-neighbor centroid matching:
- `update(rects)` — takes bounding box list, returns `{id: centroid}` dict
- Registers new objects, deregisters objects missing for `max_disappeared` frames
- Uses a distance matrix to match existing IDs to new detections

### Speed Calculation
```
pixel_displacement = sqrt(Δx² + Δy²)
real_distance = pixel_displacement × meters_per_pixel
speed_kmh = (real_distance / Δtime_seconds) × 3.6
```

### Key Configuration (top of each script)
| Variable | Purpose |
|---|---|
| `METERS_PER_PIXEL` | Calibration: real-world scale (default 0.05 = 10m / 200px) |
| `ROI_Y_MIN / ROI_Y_MAX` | Vertical region where speed is measured |
| `VEHICLE_CLASSES` | COCO class IDs: car=2, motorcycle=3, bus=5, truck=7 |
| `CONFIDENCE_THRESHOLD` | YOLO detection minimum confidence |

## Script Inventory

| File | Status | Notes |
|---|---|---|
| `speed_detection_test3.py` | Production-ready | MP4 + RTSP, video output, progress bar |
| `speed_detection_test2.py` | Production-ready | RTSP, color-coded speed display, GPU support |
| `speed_detection_test1.py` | Partial | Background subtraction + line-crossing approach |
| `Speed Detection Test 2.py` | Reference | Simplified educational version |
| `Speed Detection Test 3.py` | Reference | Minimal YOLO11 example (~82 lines) |
| `Speed Detection Test 1.py` | Incomplete | Depends on missing `engine/` module |
| `Object Tracking Test.py` | Incomplete | Tkinter GUI experiment with OpenCV Boosting tracker |

## Calibration

The `meters_per_pixel` value must be measured per camera installation. Approach: identify two points with a known real-world distance in the frame (e.g., road markings), measure their pixel distance, then `meters_per_pixel = real_meters / pixel_distance`. The ROI Y bounds should bracket the calibrated region.
