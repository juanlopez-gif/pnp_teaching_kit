"""
define_zone.py - draw the robot ACTUATION zone on the pick camera.

Saves zone.json (a polygon). detector_node.py only publishes pieces whose
centre falls inside this polygon, so the robot never tries to pick something
outside its reachable area.

Controls
--------
    left click   add a polygon vertex
    Z            undo last point
    SPACE        save (needs >= 3 points)
    Q            quit without saving
"""
import sys
import json
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CAMERA_ID, FRAME_W, FRAME_H, ZONE_FILE

WIN = "define_zone | click=point  Z=undo  SPACE=save  Q=quit"


def main():
    cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(f"[OK] Camera {CAMERA_ID}. Click the robot actuation area (>= 3 points).")

    pts = []

    def on_mouse(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            pts.append([x, y])
            print(f"  Point {len(pts)}: ({x}, {y})")

    cv2.namedWindow(WIN)
    cv2.setMouseCallback(WIN, on_mouse)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        vis = frame.copy()
        if len(pts) >= 2:
            for i in range(len(pts) - 1):
                cv2.line(vis, tuple(pts[i]), tuple(pts[i+1]), (0, 200, 255), 2)
        if len(pts) >= 3:
            cv2.line(vis, tuple(pts[-1]), tuple(pts[0]), (0, 200, 255), 1)
            ov = vis.copy()
            cv2.fillPoly(ov, [np.array(pts, np.int32)], (0, 200, 255))
            cv2.addWeighted(ov, 0.15, vis, 0.85, 0, vis)
        for i, p in enumerate(pts):
            cv2.circle(vis, tuple(p), 6, (0, 255, 100), -1)
            cv2.putText(vis, str(i+1), (p[0]+8, p[1]+6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)
        ready = len(pts) >= 3
        cv2.putText(vis, f"Points: {len(pts)}{'  - SPACE to save' if ready else ''}",
                    (10, FRAME_H - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 220, 50) if ready else (0, 120, 255), 2)
        cv2.imshow(WIN, vis)

        k = cv2.waitKey(1) & 0xFF
        if k in (ord('q'), ord('Q')):
            break
        elif k in (ord('z'), ord('Z')) and pts:
            pts.pop()
        elif k == ord(' '):
            if len(pts) < 3:
                print("[!] Need at least 3 points.")
            else:
                ZONE_FILE.write_text(json.dumps(pts, indent=2))
                print(f"[OK] Zone saved -> {ZONE_FILE}  ({len(pts)} points)")
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
