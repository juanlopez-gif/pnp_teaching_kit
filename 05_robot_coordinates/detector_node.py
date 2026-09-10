"""
detector_node.py - ROS 2 node: YOLO + homography -> publish piece coordinates.

Reads the pick camera, detects pieces with YOLO, keeps only those inside the
actuation zone (zone.json), converts each centre to robot mm via the homography,
and publishes them as JSON on PIECE_TOPIC_OUT. It does NOT move the robot;
pick_node.py does that.

Published topic
---------------
    PIECE_TOPIC_OUT  (std_msgs/String)
    payload JSON:  {"type": <class>, "conf": <float>, "x_mm": <float>, "y_mm": <float>}

Run
---
    source /opt/ros/jazzy/setup.bash
    source ~/ros2_ws/install/setup.bash
    python3 detector_node.py
"""
import sys
import json
import threading
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (CAMERA_ID, FRAME_W, FRAME_H, HOMOGRAPHY_FILE, ZONE_FILE,
                    YOLO_MODEL_PATH, CONF_THRESH, PIECE_TOPIC_OUT)
from homography_utils import load_homography, pixel_to_robot

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: pip install ultralytics"); raise SystemExit(1)

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

WIN = "Detector | Q=quit"


def point_in_polygon(pts, x, y):
    return cv2.pointPolygonTest(
        np.array(pts, dtype=np.float32), (float(x), float(y)), False) >= 0


class DetectorNode(Node):
    def __init__(self):
        super().__init__("robot2_detector")
        self._H = load_homography(HOMOGRAPHY_FILE)
        self._zone = json.loads(Path(ZONE_FILE).read_text())
        self._model = YOLO(str(YOLO_MODEL_PATH))
        self._pub = self.create_publisher(String, PIECE_TOPIC_OUT, 10)
        self.get_logger().info(f"Detector ready - publishing on {PIECE_TOPIC_OUT}")

        cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap = cap

        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        zone, H = self._zone, self._H
        cv2.namedWindow(WIN)
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                continue
            results = self._model(frame, conf=0.01, verbose=False)
            boxes = results[0].boxes
            names = results[0].names
            vis = frame.copy()

            arr = np.array(zone, np.int32)
            ov = vis.copy()
            cv2.fillPoly(ov, [arr], (0, 180, 255))
            cv2.addWeighted(ov, 0.15, vis, 0.85, 0, vis)
            cv2.polylines(vis, [arr], True, (0, 180, 255), 2)

            for box in boxes:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx, cy = (x1+x2)/2, (y1+y2)/2
                cls_name = names[int(box.cls[0])]

                if not point_in_polygon(zone, cx, cy):
                    cv2.rectangle(vis, (int(x1), int(y1)), (int(x2), int(y2)), (60, 60, 60), 1)
                    continue

                color = (0, 255, 80) if conf >= CONF_THRESH else (0, 140, 255)
                x_mm, y_mm = pixel_to_robot(cx, cy, H)
                cv2.rectangle(vis, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.circle(vis, (int(cx), int(cy)), 6, color, -1)
                cv2.putText(vis, f"{cls_name} {conf:.2f}", (int(x1), int(y1)-8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.putText(vis, f"({x_mm:.1f},{y_mm:.1f})mm", (int(x1), int(y2)+16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

                if conf >= CONF_THRESH:
                    msg = String()
                    msg.data = json.dumps({
                        "type": cls_name, "conf": round(conf, 3),
                        "x_mm": round(x_mm, 2), "y_mm": round(y_mm, 2)})
                    self._pub.publish(msg)

            cv2.imshow(WIN, vis)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                self._running = False
                break
        cv2.destroyAllWindows()

    def destroy_node(self):
        self._running = False
        self._cap.release()
        super().destroy_node()


def main():
    rclpy.init()
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
