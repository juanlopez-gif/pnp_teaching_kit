# Chapter 0 — Introduction & Exercises

Welcome. This kit teaches the **pieces of a real camera → robot pick-and-place
system**, one at a time. The goal *for now* is that you understand each piece on
its own — how it works and how you'd build it. Wiring them all together into one
running system comes **later**.

---

## 1. What is the system?

A small manufacturing cell with:

- **4 conveyor belts** (`conveyor1`…`conveyor4`), each watched by **one camera**.
- **2 USB webcams** (Logitech C920) providing those views.
- A **Niryo Ned robot** with a **vacuum gripper** that picks pieces off a belt.
- (Later) a **database** and **ROS 2 topics** that connect everything.

Your job across these exercises: make the cameras *see*, make the model *learn*,
and make the robot *know where to go*.

## 2. Two different "vision" jobs

It is important not to confuse them — they use different techniques:

| Job | Question it answers | Technique | Module |
|-----|---------------------|-----------|--------|
| **Object detection** | *What piece is where?* | YOLO (trained on your images) | 03 + 05 |
| **Motion detection** | *Is the belt moving?* | Optical flow + a small classifier | 04 |

They share the cameras but are separate models.

## 3. The coordinate idea (the robot part)

The heart of the robot exercise:

```
 camera pixel (cx,cy)  ──homography──▶  table mm (x,y)  ──pick model (IDW)──▶  6 joint angles
```

- The **homography** is a fixed camera→table calibration (ships with the kit).
- The **pick model** is what you *teach*: put a piece down, drive the robot onto
  it, save the joint angles. Repeat a few times. For any new position it
  interpolates the joints. **No ArUco, no markers — just position → joints.**

## 4. The puzzle pieces (modules)

| Module | Piece |
|--------|-------|
| [`01_cameras`](../01_cameras/) | See which cameras exist, their indices, and which zone each points at. |
| [`02_rois`](../02_rois/) | Draw and name the regions each camera cares about. |
| [`03_dataset`](../03_dataset/) | Capture images (from chosen cameras) to train YOLO. |
| [`04_conveyor_training`](../04_conveyor_training/) | Train "moving / stopped" for a belt. |
| [`05_robot_coordinates`](../05_robot_coordinates/) | Teach the dynamic pick (position → joints). |
| `06_system_integration` | *Parked for later — not part of these exercises.* |

The one file that ties it together: [`../config.py`](../config.py) — the
**camera → zone** map and all shared paths. Edit it once.

---

## 5. Setup (do this once)

```bash
cd pnp_teaching_kit
python3 -m venv venv          # or reuse the project's venv
source venv/bin/activate
pip install -r requirements.txt
```

- Modules **01–04** need only Python (OpenCV, NumPy, scikit-learn, Ultralytics).
- Module **05** additionally needs **ROS 2** + the robot:
  `source /opt/ros/jazzy/setup.bash` (and the workspace).
- You also need a trained YOLO model `best.pt` — path set in `config.py`.

---

## 6. The exercises

Each exercise is self-contained. Do them in order.

### Exercise 1 — Cameras & zones  ·  `01_cameras`
**Goal:** know your hardware.
```bash
python3 01_cameras/detect_cameras.py     # which cameras & indices are real
python3 01_cameras/view_cameras.py       # look at them live
```
Then edit `config.py → CAMERA_ZONES` so each index maps to the right belt.
**Done when:** `view_cameras.py` labels every tile with the correct zone.

### Exercise 2 — Dataset & YOLO  ·  `03_dataset`
**Goal:** understand how the piece detector is made.
```bash
python3 03_dataset/capture_dataset.py 0 4     # capture from chosen cameras
```
1. Capture varied images (positions, lighting, some empty belts).
2. Label the pieces with **Roboflow** (bounding box + class).
3. Train YOLO (`yolo detect train ...`), get `best.pt`, point `config.py` at it.
**Done when:** you can explain the flow images → labels → trained model.

*(Optional helper: `02_rois/define_rois.py` to draw the named regions the later
modules use.)*

### Exercise 3 — Conveyor training  ·  `04_conveyor_training`
**Goal:** understand training a "moving / stopped" detector.
```bash
python3 04_conveyor_training/train_conveyor.py --zone conveyor2
```
1. Draw the ROI over the belt.
2. Record clips: `1`=stopped, `2`=running (≥20 samples, balanced).
3. Train (aim for F1 > 0.9) and live-test.
**Done when:** you can explain why this uses **optical flow**, not YOLO, and when
`train_conveyor.py` vs `conveyor_detector.py` is used (train once vs run always).

### Exercise 4 — Dynamic pick calibration  ·  `05_robot_coordinates`
**Goal:** teach the robot to pick a piece wherever it lands.
```bash
source /opt/ros/jazzy/setup.bash
python3 05_robot_coordinates/calibrate_pick.py
```
1. For ≥6 pieces: let YOLO see it → SPACE → jog the robot onto it → it saves the joints.
2. `Q` writes `pick_model.json`.
3. Test the interpolation: `python3 05_robot_coordinates/pick_model.py`.
**Done when:** you can explain the chain *pixel → mm → joints* and why a few
taught poses + IDW are enough (no inverse kinematics).

---

## 7. Where to go next
Once each piece is clear, the next step (a later chapter) is **integration**:
running the cameras, detection, motion and robot together, publishing on ROS 2
topics and logging to the database. That lives in `06_system_integration`
(currently parked).
