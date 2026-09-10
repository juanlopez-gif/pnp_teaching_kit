"""
ConveyorDetector
================
Detects whether a conveyor belt is moving or stopped.
Output: moving (bool) + confidence (float 0-1)

Pipeline:
  - Optical flow (Farneback) over the belt ROI -> 10 features
  - GradientBoostingClassifier (scikit-learn)
  - Hysteresis (k_start / k_stop) to avoid state flickering

This is a self-contained module: import it, give it a camera index and a
model directory, teach it a few clips of "moving" vs "stopped", train, and
call update(frame) in your loop.
"""

import cv2
import numpy as np
import time
import json
import pickle
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple
from collections import deque

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import warnings
warnings.filterwarnings("ignore")


# ── Data structures ──────────────────────────────────────────────────────────────

@dataclass
class FlowFeatures:
    mean_magnitude: float
    median_magnitude: float
    p90_magnitude: float
    std_magnitude: float
    mean_angle_x: float
    mean_angle_y: float
    coherence: float
    temporal_consistency: float
    pixel_diff_mean: float
    pixel_diff_std: float

    def to_array(self) -> np.ndarray:
        return np.array(list(asdict(self).values()), dtype=np.float32)


@dataclass
class ConveyorState:
    moving: bool
    confidence: float
    timestamp: float


# ── Feature extractor ────────────────────────────────────────────────────────────

class FlowFeatureExtractor:
    """Turns a stream of ROI frames into optical-flow feature vectors."""

    FARNEBACK = dict(pyr_scale=0.5, levels=3, winsize=15,
                     iterations=3, poly_n=5, poly_sigma=1.2, flags=0)

    def __init__(self, history_len: int = 5, frame_skip: int = 2):
        self._buf: deque = deque(maxlen=frame_skip + 1)
        self._prev_flow: Optional[np.ndarray] = None
        self._history: deque = deque(maxlen=history_len)
        self._acc_dt: float = 0.0

    def reset(self):
        self._buf.clear()
        self._prev_flow = None
        self._history.clear()
        self._acc_dt = 0.0

    def extract(self, roi_bgr: np.ndarray, dt: float) -> Optional[FlowFeatures]:
        gray = cv2.equalizeHist(cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY))
        self._buf.append(gray)
        self._acc_dt += dt
        if len(self._buf) < self._buf.maxlen:
            return None

        elapsed = self._acc_dt
        self._acc_dt = 0.0
        ref = self._buf[0]
        flow = cv2.calcOpticalFlowFarneback(ref, gray, None, **self.FARNEBACK)
        fps = flow / elapsed if elapsed > 0 else flow
        mag, ang = cv2.cartToPolar(fps[..., 0], fps[..., 1])

        # Coherence: fraction of the flow field pointing the same way (belt motion
        # is coherent; noise is not).
        dom_ang = float(np.median(ang.ravel()))
        adiff = np.minimum(np.abs(ang - dom_ang), 2 * np.pi - np.abs(ang - dom_ang))
        coherence = float(np.mean(adiff < np.deg2rad(30)))

        # Temporal consistency: correlation of magnitude with the previous flow.
        if self._prev_flow is not None:
            pm, _ = cv2.cartToPolar(self._prev_flow[..., 0], self._prev_flow[..., 1])
            a, b = mag.ravel(), pm.ravel()
            tc = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 1.0
        else:
            tc = 0.0

        diff = cv2.absdiff(ref, gray).astype(np.float32)
        feat = FlowFeatures(
            mean_magnitude=float(mag.mean()),
            median_magnitude=float(np.median(mag)),
            p90_magnitude=float(np.percentile(mag, 90)),
            std_magnitude=float(mag.std()),
            mean_angle_x=float(fps[..., 0].mean()),
            mean_angle_y=float(fps[..., 1].mean()),
            coherence=coherence,
            temporal_consistency=tc,
            pixel_diff_mean=float(diff.mean()),
            pixel_diff_std=float(diff.std()),
        )
        self._prev_flow = flow.copy()
        self._history.append(feat)
        return feat


# ── ML classifier ────────────────────────────────────────────────────────────────

class ConveyorClassifier:
    def __init__(self):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=200, max_depth=4,
                learning_rate=0.05, subsample=0.8, random_state=42,
            )),
        ])
        self._X: List[np.ndarray] = []
        self._y: List[int] = []
        self.trained: bool = False

    def add_sample(self, feat: FlowFeatures, label: int):
        self._X.append(feat.to_array())
        self._y.append(label)

    def train(self, cv_folds: int = 5) -> dict:
        if len(self._X) < 20:
            raise ValueError("You need at least 20 samples.")
        X = np.vstack(self._X)
        y = np.array(self._y)
        print(f"[ML] Training with {len(y)} samples  (stopped={sum(y==0)}, moving={sum(y==1)})")
        scores = cross_val_score(self.pipeline, X, y, cv=cv_folds, scoring="f1")
        self.pipeline.fit(X, y)
        self.trained = True
        print(f"[ML] CV F1 = {scores.mean():.3f} +/- {scores.std():.3f}")
        return {"cv_f1_mean": float(scores.mean()),
                "cv_f1_std": float(scores.std()), "n_samples": len(y)}

    def predict(self, feat: FlowFeatures) -> Tuple[bool, float]:
        if not self.trained:
            # Fallback heuristic before any training exists.
            moving = feat.p90_magnitude > 1.5
            return moving, float(moving)
        x = feat.to_array().reshape(1, -1)
        label = int(self.pipeline.predict(x)[0])
        prob = float(self.pipeline.predict_proba(x)[0][1])
        return bool(label), prob

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({"pipeline": self.pipeline, "X": self._X,
                         "y": self._y, "trained": self.trained}, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.pipeline = d["pipeline"]
        self._X = d["X"]
        self._y = d["y"]
        self.trained = d["trained"]


# ── Hysteresis (debounce) ────────────────────────────────────────────────────────

class Hysteresis:
    """Requires k_start consecutive 'moving' frames to switch ON and k_stop
    consecutive 'stopped' frames to switch OFF, so the state never flickers."""

    def __init__(self, k_start: int = 5, k_stop: int = 8):
        self.k_start = k_start
        self.k_stop = k_stop
        self._state = False
        self._mc = 0
        self._sc = 0

    def update(self, moving_prob: float, threshold: float = 0.5) -> bool:
        if moving_prob >= threshold:
            self._mc += 1
            self._sc = 0
        else:
            self._sc += 1
            self._mc = 0
        if not self._state and self._mc >= self.k_start:
            self._state = True
        elif self._state and self._sc >= self.k_stop:
            self._state = False
        return self._state


# ── Main detector ────────────────────────────────────────────────────────────────

class ConveyorDetector:
    def __init__(self, camera_id: int = 0, model_dir: str = "./conveyor_model",
                 k_start: int = 5, k_stop: int = 8):
        self.camera_id = camera_id
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.roi: Optional[list] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.extractor = FlowFeatureExtractor()
        self.classifier = ConveyorClassifier()
        self.hysteresis = Hysteresis(k_start=k_start, k_stop=k_stop)
        self._last_t: float = 0.0

    # ── Camera ──────────────────────────────────────────────────────────────────
    def _open(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)

    def _read(self) -> Optional[np.ndarray]:
        self._open()
        ok, frame = self.cap.read()
        return frame if ok else None

    def _crop(self, frame: np.ndarray) -> np.ndarray:
        """Crop to the ROI polygon's bounding box and mask out everything else."""
        if self.roi is None:
            return frame
        pts = np.array(self.roi, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        crop = frame[y:y+h, x:x+w].copy()
        mask = np.zeros(crop.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [pts - np.array([x, y])], 255)
        crop[mask == 0] = 0
        return crop

    # ── ROI setup ────────────────────────────────────────────────────────────────
    def setup_roi(self):
        frame = self._read()
        if frame is None:
            raise RuntimeError("Cannot read from camera.")
        points = []

        def redraw():
            img = frame.copy()
            for i, p in enumerate(points):
                cv2.circle(img, p, 6, (0, 255, 0), -1)
                cv2.putText(img, str(i+1), (p[0]+8, p[1]-8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if len(points) > 1:
                for i in range(len(points)-1):
                    cv2.line(img, points[i], points[i+1], (0, 255, 0), 2)
            if len(points) >= 3:
                cv2.line(img, points[-1], points[0], (0, 255, 0), 2)
                ov = img.copy()
                cv2.fillPoly(ov, [np.array(points)], (0, 255, 0))
                img = cv2.addWeighted(img, 0.7, ov, 0.3, 0)
            n = len(points)
            hint = "ENTER=confirm" if n >= 3 else f"need {3-n} more point(s)"
            cv2.putText(img, f"{n} pts | Z=undo  R=reset  {hint}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            cv2.imshow("ROI", img)

        def click(event, x, y, *_):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                redraw()

        cv2.imshow("ROI", frame)
        cv2.setMouseCallback("ROI", click)
        redraw()
        print("Click = add point | ENTER = confirm | Z = undo | ESC = cancel")
        while True:
            k = cv2.waitKey(20) & 0xFF
            if k == 13 and len(points) >= 3:
                break
            elif k in (ord('z'), ord('Z')) and points:
                points.pop(); redraw()
            elif k in (ord('r'), ord('R')):
                points.clear(); redraw()
            elif k == 27:
                points.clear(); break
        cv2.destroyWindow("ROI")
        if len(points) >= 3:
            self.roi = points
            print(f"[ROI] {len(points)} points saved.")
            self.save()
        else:
            print("[ROI] Cancelled.")

    # ── Data collection ──────────────────────────────────────────────────────────
    def collect_training_data(self, clip_seconds: float = 5.0):
        CLASSES = {
            ord('1'): (0, "STOPPED",      (0,   0, 255)),
            ord('2'): (1, "RUNNING",      (0, 220,   0)),
            ord('6'): (0, "DECELERATING", (0, 100, 255)),
            ord('7'): (1, "ACCELERATING", (0, 255, 180)),
        }
        print("\n1=STOPPED  2=RUNNING  6=DECELERATING  7=ACCELERATING  Q=done")
        self._open()
        self.extractor.reset()
        counts = {0: 0, 1: 0}
        recording = None
        clip_name = ""
        clip_color = (255, 255, 255)
        clip_end = 0.0
        prev_t = time.time()

        while True:
            frame = self._read()
            if frame is None:
                break
            now = time.time()
            dt = max(now - prev_t, 1e-3)
            prev_t = now
            feat = self.extractor.extract(self._crop(frame), dt)

            if recording is not None and now >= clip_end:
                print(f"  OK - {clip_name}  (stopped={counts[0]}, moving={counts[1]})")
                recording = None

            if feat is not None and recording is not None:
                self.classifier.add_sample(feat, recording)
                counts[recording] += 1

            vis = frame.copy()
            if self.roi:
                col = clip_color if recording is not None else (80, 80, 80)
                cv2.polylines(vis, [np.array(self.roi, np.int32)], True, col, 2)
            h = vis.shape[0]
            cv2.rectangle(vis, (0, h-44), (vis.shape[1], h), (25, 25, 25), -1)
            if recording is not None:
                rem = max(0.0, clip_end - now)
                bar = int(vis.shape[1] * rem / clip_seconds)
                cv2.rectangle(vis, (0, h-4), (bar, h), clip_color, -1)
                cv2.putText(vis, f"REC  {clip_name}  {rem:.1f}s",
                            (10, h-16), cv2.FONT_HERSHEY_SIMPLEX, 0.6, clip_color, 2)
            else:
                cv2.putText(vis, "1=STOPPED  2=RUNNING  Q=done",
                            (10, h-16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)
            cv2.putText(vis, f"stopped={counts[0]}  moving={counts[1]}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)
            cv2.imshow("Collect data", vis)
            k = cv2.waitKey(1) & 0xFF
            if k in CLASSES and recording is None:
                label, name, color = CLASSES[k]
                recording, clip_name, clip_color = label, name, color
                clip_end = time.time() + clip_seconds
                self.extractor.reset()
                print(f"  -> Recording {clip_seconds:.0f}s of {name}...")
            elif k in (ord('q'), ord('Q')):
                break

        cv2.destroyAllWindows()
        print(f"[Data] Done.  stopped={counts[0]}  moving={counts[1]}")

    # ── Training ─────────────────────────────────────────────────────────────────
    def train(self) -> dict:
        result = self.classifier.train()
        self.save()
        return result

    # ── Inference ────────────────────────────────────────────────────────────────
    def update(self, frame: Optional[np.ndarray] = None) -> Optional[ConveyorState]:
        now = time.time()
        dt = now - self._last_t if self._last_t > 0 else 1/15
        self._last_t = now
        if frame is None:
            frame = self._read()
        if frame is None:
            return None
        feat = self.extractor.extract(self._crop(frame), dt)
        if feat is None:
            return None
        moving_raw, prob = self.classifier.predict(feat)
        moving = self.hysteresis.update(prob)
        return ConveyorState(moving=moving, confidence=prob, timestamp=now)

    # ── Live demo ────────────────────────────────────────────────────────────────
    def run(self):
        self._open()
        self.extractor.reset()
        print("[Live] Q=quit")
        while True:
            frame = self._read()
            if frame is None:
                break
            state = self.update(frame)
            vis = frame.copy()
            if self.roi:
                col = (0, 255, 0) if (state and state.moving) else (0, 0, 255)
                cv2.polylines(vis, [np.array(self.roi, np.int32)], True, col, 2)
            if state:
                label = "MOVING" if state.moving else "STOPPED"
                col = (0, 255, 80) if state.moving else (0, 60, 255)
                cv2.putText(vis, f"{label}  {state.confidence:.2f}",
                            (10, 40), cv2.FONT_HERSHEY_DUPLEX, 1.1, col, 2)
                print(f"\r[{'MOVING ' if state.moving else 'STOPPED'}]  "
                      f"conf={state.confidence:.3f}   ", end="", flush=True)
            cv2.imshow("Conveyor", vis)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
        print()

    # ── Persistence ──────────────────────────────────────────────────────────────
    def save(self):
        clf_path = self.model_dir / "classifier.pkl"
        roi_path = self.model_dir / "roi.json"
        self.classifier.save(str(clf_path))
        roi_data = [list(p) for p in self.roi] if self.roi else None
        roi_path.write_text(json.dumps(roi_data))
        n0 = sum(1 for y in self.classifier._y if y == 0)
        n1 = sum(1 for y in self.classifier._y if y == 1)
        print(f"[Save] {self.model_dir}/  (stopped={n0}, moving={n1})")

    def load(self):
        clf_path = self.model_dir / "classifier.pkl"
        roi_path = self.model_dir / "roi.json"
        if clf_path.exists():
            self.classifier.load(str(clf_path))
            n0 = sum(1 for y in self.classifier._y if y == 0)
            n1 = sum(1 for y in self.classifier._y if y == 1)
            print(f"[Load] Classifier  (stopped={n0}, moving={n1})")
        if roi_path.exists():
            data = json.loads(roi_path.read_text())
            self.roi = [tuple(p) for p in data] if data else None
            if self.roi:
                print(f"[Load] ROI  ({len(self.roi)} points)")

    def __del__(self):
        if self.cap is not None:
            self.cap.release()
