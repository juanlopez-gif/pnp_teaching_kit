#!/usr/bin/env python3
"""
Step 3 - Capture a dataset of images from the cameras.
======================================================

Grabs synchronized snapshots from the cameras you choose so you can build a
training set for the YOLO piece detector (label them later with a tool such as
Roboflow, CVAT or LabelImg).

Choose which cameras to use:
    python3 capture_dataset.py            # all cameras in config.CAMERA_ZONES
    python3 capture_dataset.py 0 4        # only indices 0 and 4

Choose the output folder:
    python3 capture_dataset.py --out my_dataset 0 4

Files are saved as:
    <OUTPUT_DIR>/cam<INDEX>_<TIMESTAMP>_<COUNTER>.jpg

Controls
--------
    SPACE   save one snapshot from every active camera
    q       quit
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

WINDOW_COLS = 2
FW, FH = config.FRAME_WIDTH, config.FRAME_HEIGHT


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
        print(f"[OK] Camera {idx} open")
    return caps


def build_mosaic(tiles):
    rows_needed = (len(tiles) + WINDOW_COLS - 1) // WINDOW_COLS
    blank = np.zeros((FH, FW, 3), np.uint8)
    while len(tiles) < rows_needed * WINDOW_COLS:
        tiles.append(blank)
    return np.vstack([np.hstack(tiles[r * WINDOW_COLS:(r + 1) * WINDOW_COLS])
                      for r in range(rows_needed)])


def save_snapshot(frames_by_cam, counter, output_dir):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for cam_idx, frame in frames_by_cam.items():
        fname = output_dir / f"cam{cam_idx}_{ts}_{counter:04d}.jpg"
        cv2.imwrite(str(fname), frame)
    print(f"[SAVE] {len(frames_by_cam)} images  ({ts}_{counter:04d})")


def main():
    parser = argparse.ArgumentParser(description="Capture a dataset from selected cameras.")
    parser.add_argument("indices", nargs="*", type=int,
                        help="camera indices to use (default: all in config.CAMERA_ZONES)")
    parser.add_argument("--out", default="dataset",
                        help="output folder name (default: dataset)")
    args = parser.parse_args()

    output_dir = Path(__file__).resolve().parent / args.out
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {output_dir}\n")

    indices = args.indices if args.indices else sorted(config.CAMERA_ZONES.keys())
    caps = open_cameras(indices)
    if not caps:
        print("No cameras available.")
        raise SystemExit(1)

    print("SPACE = save snapshot   |   q = quit\n")
    counter = 0

    while True:
        raw = {}
        tiles = []
        for cam_idx, cap in caps.items():
            ok, frame = cap.read()
            if not ok:
                blank = np.zeros((FH, FW, 3), np.uint8)
                cv2.putText(blank, f"Cam {cam_idx}: no signal", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                tiles.append(blank)
                continue
            raw[cam_idx] = frame
            disp = frame.copy()
            cv2.putText(disp, f"Cam {cam_idx}", (8, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            tiles.append(disp)

        cv2.imshow("Capture dataset | SPACE=save  q=quit", build_mosaic(tiles))
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' ') and raw:
            counter += 1
            save_snapshot(raw, counter, output_dir)

    for cap in caps.values():
        cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal snapshots: {counter}  ->  {output_dir}")


if __name__ == "__main__":
    main()
