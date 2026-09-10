#!/usr/bin/env python3
"""
Step 2 - Define named ROIs (regions of interest) per camera.
============================================================

An ROI is a polygon drawn on a camera image that names a meaningful area,
e.g. "conveyor2" or "stack_slot_1". Downstream, a detection only "counts"
if its centre falls inside an ROI. Motion (module 04) and object detection
(modules 05/06) both rely on these regions.

ROIs are saved to ../02_rois/rois.json (config.ROIS_PATH) as:

    {
      "0": [ {"pts": [[x,y], ...], "name": "conveyor4"} ],
      "2": [ {"pts": [[x,y], ...], "name": "conveyor3"} ],
      ...
    }

Controls
--------
    left click        add a vertex to the current polygon
    right click / ENTER   close the polygon -> type a name -> ENTER
    z                 undo last vertex
    c                 clear all ROIs of the camera you last clicked
    s                 save to rois.json
    q                 save and quit
"""

import sys
import json
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

WINDOW_COLS = 2
FW, FH = config.FRAME_WIDTH, config.FRAME_HEIGHT


class RoiEditor:
    def __init__(self, cam_indices):
        self.cam_indices = list(cam_indices)
        self.rois = {i: [] for i in cam_indices}   # cam -> [ {pts, name}, ... ]
        self.current = []                          # vertices being drawn
        self.active_cam = None
        # text-input state while naming a freshly closed polygon
        self.naming = False
        self.typed = ""
        self.pending_pts = None
        self.pending_cam = None

    # ── persistence ──────────────────────────────────────────────────────────
    def load(self, path):
        if not Path(path).exists():
            return
        data = json.loads(Path(path).read_text())
        for k, rois in data.items():
            idx = int(k)
            if idx in self.rois:
                self.rois[idx] = rois
        print(f"[ROI] Loaded from {path}")

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {str(k): v for k, v in self.rois.items()}
        Path(path).write_text(json.dumps(data, indent=2))
        print(f"[ROI] Saved -> {path}")

    # ── mosaic coordinate mapping ────────────────────────────────────────────
    def mosaic_to_cam(self, mx, my):
        col, row = mx // FW, my // FH
        pos = row * WINDOW_COLS + col
        if pos >= len(self.cam_indices):
            return None
        return self.cam_indices[pos], mx - col * FW, my - row * FH

    # ── mouse ────────────────────────────────────────────────────────────────
    def on_mouse(self, event, mx, my, *_):
        if self.naming:
            return
        hit = self.mosaic_to_cam(mx, my)
        if hit is None:
            return
        cam, lx, ly = hit
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.active_cam is not None and self.active_cam != cam:
                self.current = []
            self.active_cam = cam
            self.current.append([lx, ly])
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.close_polygon()

    # ── naming ───────────────────────────────────────────────────────────────
    def close_polygon(self):
        if self.active_cam is None or len(self.current) < 3:
            return
        self.pending_pts = self.current.copy()
        self.pending_cam = self.active_cam
        self.current = []
        self.typed = ""
        self.naming = True

    def handle_naming_key(self, key):
        if key == 13:            # ENTER -> confirm
            name = self.typed.strip() or f"ROI_{len(self.rois[self.pending_cam]) + 1}"
            self.rois[self.pending_cam].append({"pts": self.pending_pts, "name": name})
            print(f"[ROI] '{name}' saved on camera {self.pending_cam}")
            self.naming = False
        elif key == 27:          # ESC -> auto name
            self.typed = ""
            self.handle_naming_key(13)
        elif key == 8:           # backspace
            self.typed = self.typed[:-1]
        elif 32 <= key <= 126:
            self.typed += chr(key)

    # ── drawing ──────────────────────────────────────────────────────────────
    def draw(self, frame, cam):
        overlay = frame.copy()
        for roi in self.rois[cam]:
            pts = np.array(roi["pts"], np.int32)
            cv2.fillPoly(overlay, [pts], (0, 200, 0))
            cv2.polylines(frame, [pts], True, (0, 200, 0), 2)
            cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
            cv2.putText(frame, roi["name"], (cx - 20, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        if self.active_cam == cam and self.current:
            for p in self.current:
                cv2.circle(frame, tuple(p), 5, (0, 255, 255), -1)
            if len(self.current) > 1:
                cv2.polylines(frame, [np.array(self.current, np.int32)],
                              False, (0, 255, 255), 1)
        zone = config.CAMERA_ZONES.get(cam, "unassigned")
        cv2.putText(frame, f"cam {cam} ({zone})  ROIs:{len(self.rois[cam])}",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)


def open_cameras(indices):
    caps = {}
    for idx in indices:
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(f"[WARN] Could not open camera {idx}")
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FW)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FH)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        caps[idx] = cap
    return caps


def build_mosaic(tiles):
    rows_needed = (len(tiles) + WINDOW_COLS - 1) // WINDOW_COLS
    blank = np.zeros((FH, FW, 3), np.uint8)
    while len(tiles) < rows_needed * WINDOW_COLS:
        tiles.append(blank)
    return np.vstack([np.hstack(tiles[r * WINDOW_COLS:(r + 1) * WINDOW_COLS])
                      for r in range(rows_needed)])


def draw_name_box(mosaic, typed):
    h, w = mosaic.shape[:2]
    x0, y0, bw, bh = (w - 500) // 2, (h - 80) // 2, 500, 80
    ov = mosaic.copy()
    cv2.rectangle(ov, (x0, y0), (x0 + bw, y0 + bh), (20, 20, 20), -1)
    cv2.addWeighted(ov, 0.85, mosaic, 0.15, 0, mosaic)
    cv2.rectangle(mosaic, (x0, y0), (x0 + bw, y0 + bh), (200, 200, 200), 2)
    cv2.putText(mosaic, "ROI name (ENTER=ok  ESC=auto):", (x0 + 10, y0 + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(mosaic, typed + "|", (x0 + 10, y0 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


def main():
    indices = sorted(config.CAMERA_ZONES.keys())
    caps = open_cameras(indices)
    if not caps:
        print("No cameras available.")
        raise SystemExit(1)

    editor = RoiEditor(list(caps.keys()))
    editor.load(config.ROIS_PATH)

    win = "Define ROIs | left=vertex right/ENTER=close z=undo c=clear s=save q=quit"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, editor.on_mouse)

    while True:
        tiles = []
        for cam, cap in caps.items():
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((FH, FW, 3), np.uint8)
            editor.draw(frame, cam)
            tiles.append(frame)
        mosaic = build_mosaic(tiles)
        if editor.naming:
            draw_name_box(mosaic, editor.typed)
        cv2.imshow(win, mosaic)

        key = cv2.waitKey(1) & 0xFF
        if editor.naming:
            editor.handle_naming_key(key)
            continue
        if key == ord('q'):
            editor.save(config.ROIS_PATH)
            break
        elif key == ord('s'):
            editor.save(config.ROIS_PATH)
        elif key == 13:
            editor.close_polygon()
        elif key in (ord('z'), ord('Z')) and editor.current:
            editor.current.pop()
        elif key == ord('c') and editor.active_cam is not None:
            editor.rois[editor.active_cam] = []
            print(f"[ROI] Cleared camera {editor.active_cam}")

    for cap in caps.values():
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
