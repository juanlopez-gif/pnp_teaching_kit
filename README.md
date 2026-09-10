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

## Operating guide (the two things people always ask)

### A) From dataset → Roboflow labeling → YOLO training on a GPU
Short version (full step-by-step in [`03_dataset/README.md`](03_dataset/README.md)):

```bash
# 1. Capture images from the cameras you choose
python3 03_dataset/capture_dataset.py 0 4

# 2. Label in Roboflow (roboflow.com): Object Detection project ->
#    upload 03_dataset/dataset/ -> draw a box + class on every piece ->
#    Generate version (Resize 640) -> Export as "YOLOv8"

# 3. Move the exported dataset to a machine WITH a GPU (lab PC or Colab):
scp roboflow_export.zip user@gpu-host:~/pieces/      # or use Roboflow's download snippet

# 4. Train on the GPU machine
pip install ultralytics
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"   # must be True
yolo detect train data=path/to/data.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16 device=0

# 5. Bring the model back and point the kit at it
scp user@gpu-host:~/runs/detect/train/weights/best.pt ./best.pt   # -> config.YOLO_MODEL_PATH
```

### B) Starting the robot
Short version (full step-by-step in [`05_robot_coordinates/README.md`](05_robot_coordinates/README.md)):

```bash
# 1. Power on the robot; make sure it is reachable (ping its hostname/IP)

# 2. Source ROS 2 + workspace
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# 3. Set the robot's namespace + IP in the driver config:
#    ~/ros2_ws/src/ned-ros2-driver/niryo_ned_ros2_driver/config/drivers_list.yaml
#      robot_namespaces: ["robot2"]     robot_ips: ["ned2-aa-bbb-ccc.local"]

# 4. Launch the driver (bridges ROS 2 <-> the physical robot)
ros2 launch niryo_ned_ros2_driver driver.launch.py

# 5. Verify
ros2 node list                     # expect /ros2_driver_robot2
ros2 topic echo --once /robot2/joint_states

# 6. Now run vision + pick (each in its own terminal)
cd 05_robot_coordinates
./launch_detector.sh               # publishes /robot2/piece_detected
./launch_pick.sh                   # moves the arm to pick
```
The driver in step 4 **must** be running before `calibrate_pick.py` or
`pick_node.py`, or they will hang waiting for the robot.

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
