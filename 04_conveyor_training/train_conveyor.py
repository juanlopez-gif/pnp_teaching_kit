#!/usr/bin/env python3
"""
Step 4 - Train the "moving / stopped" detector for one conveyor.
================================================================

Interactive tool around ConveyorDetector. You pick a zone (by name), it uses
the camera assigned to that zone in config.CAMERA_ZONES and stores its model
in config.CONVEYOR_MODEL_DIRS[zone].

Usage
-----
    python3 train_conveyor.py --zone conveyor2
    python3 train_conveyor.py --zone conveyor4

Typical first run:  1 (draw ROI) -> 2 (collect several clips) -> 3 (train) -> 4 (test)
State is saved automatically after each step and on exit.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from conveyor_detector import ConveyorDetector

MENU = """
+--------------------------------------+
|    ConveyorDetector - Training       |
+--------------------------------------+
|  1  Draw ROI                         |
|  2  Collect training data            |
|  3  Train model                      |
|  4  Live test                        |
|  0  Exit (saves automatically)       |
+--------------------------------------+
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", default="conveyor2",
                        choices=list(config.CAMERA_ZONES.values()),
                        help="Which zone/belt to train (name from config.CAMERA_ZONES)")
    args = parser.parse_args()

    camera_id = config.ZONE_CAMERAS[args.zone]
    model_dir = config.CONVEYOR_MODEL_DIRS[args.zone]
    print(f"\n[{args.zone}]  camera={camera_id}  model={model_dir}")

    det = ConveyorDetector(camera_id=camera_id, model_dir=str(model_dir))

    try:
        det.load()
        print("[OK] Previous state loaded.")
    except Exception:
        print("[INFO] No previous state - starting from scratch.")

    while True:
        print(MENU)
        opt = input("Option: ").strip()

        if opt == "1":
            print("\n[ROI] Opening camera to draw ROI...")
            print("  Left click = add point")
            print("  ENTER = confirm  |  Z = undo  |  R = reset  |  ESC = cancel")
            det.setup_roi()
            if det.roi:
                det.save()

        elif opt == "2":
            if det.roi is None:
                print("[!] Define the ROI first (option 1).")
                continue
            secs = input("Clip duration in seconds [5]: ").strip()
            secs = float(secs) if secs else 5.0
            det.collect_training_data(clip_seconds=secs)
            det.save()

        elif opt == "3":
            try:
                result = det.train()
                print(f"\n[Train] F1 CV = {result['cv_f1_mean']:.3f} +/- {result['cv_f1_std']:.3f}"
                      f"  ({result['n_samples']} samples)")
            except ValueError as e:
                print(f"[!] {e}")

        elif opt == "4":
            if det.roi is None:
                print("[!] Define the ROI first (option 1).")
                continue
            print("[Live] Q=quit")
            det.run()

        elif opt == "0":
            det.save()
            print("Exiting.")
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
