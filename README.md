# Pick-and-Place Vision Teaching Kit

A clean, step-by-step version of a real camera → robot → database pipeline,
built for **teaching**. Everything is in English and organized so you can learn
one concept at a time.

You will go from *"how many cameras do I have?"* all the way to *"the robot picks
a detected piece and the result is logged in a database"*.

---

## What's inside

> **Start here:** [`00_introduction`](00_introduction/) — overview + the class exercises.

| Module | Topic | Start here |
|--------|-------|-----------|
| [`00_introduction`](00_introduction/) | Overview of the system + the exercises | `README.md` |
| [`01_cameras`](01_cameras/) | Detect cameras, find indices, assign index → zone | `detect_cameras.py` |
| [`02_rois`](02_rois/) | Draw & name regions of interest per camera | `define_rois.py` |
| [`03_dataset`](03_dataset/) | Capture images (choose cameras) to train YOLO | `capture_dataset.py` |
| [`04_conveyor_training`](04_conveyor_training/) | Train "moving / stopped" per belt | `train_conveyor.py` |
| [`05_robot_coordinates`](05_robot_coordinates/) | Dynamic robot pick: position → joints | `calibrate_pick.py` |
| [`06_system_integration`](06_system_integration/) | ROS 2 topics + PostgreSQL logging — **later, not a core exercise yet** | `vision_logger_reference.py` |
| [`docs`](docs/) | Architecture, ROS topics, database | `ARCHITECTURE.md` |

The single most important file is [`config.py`](config.py): it holds the
**camera → zone** map and every shared path/topic. Edit it once; every module
follows.

## The class exercises (understand each puzzle piece)

The point right now is to **understand the pieces on their own**; integrating
them into one running system comes later.

1. **Cameras** — which cameras are available, which you can use, and which zone
   each one points at. → `01_cameras`
2. **Dataset** — capture images from the cameras you pick, label them (Roboflow),
   train YOLO. → `03_dataset`
3. **Conveyor training** — understand how "moving / stopped" is trained and how
   it works. → `04_conveyor_training`
4. **Dynamic pick calibration** — teach the robot to pick a piece wherever it is
   (position → jog → save joints → interpolate). → `05_robot_coordinates`

(`02_rois` is a small helper used by 04/05/06. `06_system_integration` is
parked for later.)

---

## Quick start

```bash
# From the kit folder
cd pnp_teaching_kit

# 1. Install Python deps (ROS 2 is separate — only modules 05/06 need it)
pip install -r requirements.txt

# 2. Which cameras do I have, and at what indices?
python3 01_cameras/detect_cameras.py

# 3. Look at them and confirm which belt is which
python3 01_cameras/view_cameras.py

# 4. Edit config.py -> CAMERA_ZONES to match your wiring

# 5. Draw the regions each camera should watch
python3 02_rois/define_rois.py
```

Then continue module by module (03 → 06). Each folder has its own README.

---

## The big picture

```
 cameras ─▶ YOLO (what piece, where) ─┬─▶ robot pick (module 05)
                                      └─▶ database log (module 06)
 cameras ─▶ optical flow (belt moving?) ─▶ verify vs expected (module 04)
```

Two vision jobs share the cameras:
- **YOLO** answers *what is where* (object detection).
- **Optical flow** answers *is it moving* (motion detection).

Full details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Assign "camera 0 → zone 1"

That assignment is just a dictionary in [`config.py`](config.py):

```python
CAMERA_ZONES = {
    0: "conveyor4",
    2: "conveyor3",
    4: "conveyor2",   # the belt the robot picks from
    6: "conveyor1",
}
```

Run `01_cameras/detect_cameras.py` to get the real indices, then edit this map.
Everything else (ROIs, training, logging) reads from it.

---

## Requirements

- Python 3.10+ with the packages in `requirements.txt`
  (`opencv-python`, `numpy`, `scikit-learn`, `ultralytics`, `psycopg2-binary`).
- A trained YOLO model `best.pt` (path set by `config.YOLO_MODEL_PATH`).
- **Only for modules 05 & 06:** ROS 2 Jazzy + the Niryo interfaces, sourced with
  `source /opt/ros/jazzy/setup.bash`. Modules 01–04 run without ROS 2.
- **Only for module 06:** a reachable PostgreSQL database.

---

## Notes
- The calibration data shipped in `05_robot_coordinates` (`homography.npy`,
  `pick_model.json`, …) is real reference data from the original cell. Re-run
  calibration for your own camera/robot placement.
- Robot joint poses and the vacuum tool id in `pick_node.py` are cell-specific —
  re-teach them for your hardware.
