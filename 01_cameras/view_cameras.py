#!/usr/bin/env python3
"""
Step 1b - View the cameras live and confirm the index <-> zone assignment.
=========================================================================

Opens every camera listed in config.CAMERA_ZONES and shows them in a grid,
each tile labelled with its index and the zone it is assigned to. Use this
to physically confirm "index 0 really is the belt I call conveyor4", then
fix config.CAMERA_ZONES if any label is wrong.

You can also pass explicit indices to just look at raw feeds:
    python3 view_cameras.py 0 2 4 6

Controls
--------
    q / ESC   quit
    s         save a snapshot of the grid (mosaic_NNN.jpg)
"""

import sys
from pathlib import Path

import cv2
import numpy as np

# Make the kit root importable so `import config` works from any folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


WINDOW_COLS = 2


def open_cameras(indices):
    caps = {}
    for idx in indices:
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(f"[WARN] Could not open camera index {idx}")
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        caps[idx] = cap
        print(f"[OK] Camera {idx} open")
    return caps


def build_mosaic(tiles):
    """Stack labelled frames into a grid mosaic."""
    rows_needed = (len(tiles) + WINDOW_COLS - 1) // WINDOW_COLS
    blank = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    while len(tiles) < rows_needed * WINDOW_COLS:
        tiles.append(blank)
    rows = [np.hstack(tiles[r * WINDOW_COLS:(r + 1) * WINDOW_COLS])
            for r in range(rows_needed)]
    return np.vstack(rows)


def main():
    # Indices from the command line, or fall back to the config map.
    if len(sys.argv) > 1:
        indices = [int(a) for a in sys.argv[1:]]
    else:
        indices = sorted(config.CAMERA_ZONES.keys())

    print(f"Opening cameras: {indices}")
    caps = open_cameras(indices)
    if not caps:
        print("No cameras available.")
        raise SystemExit(1)

    win = "Camera viewer | q=quit  s=snapshot"
    snap = 0

    while True:
        tiles = []
        for idx, cap in caps.items():
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), np.uint8)
                cv2.putText(frame, f"Cam {idx}: no signal", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            zone = config.CAMERA_ZONES.get(idx, "unassigned")
            label = f"index {idx}  ->  {zone}"
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 30), (0, 0, 0), -1)
            cv2.putText(frame, label, (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            tiles.append(frame)

        mosaic = build_mosaic(tiles)
        cv2.imshow(win, mosaic)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord('s'):
            snap += 1
            fname = f"mosaic_{snap:03d}.jpg"
            cv2.imwrite(fname, mosaic)
            print(f"[SAVE] {fname}")

    for cap in caps.values():
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
