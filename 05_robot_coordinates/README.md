# Module 05 — Dynamic robot pick

Goal: teach the robot to pick a piece **wherever it lands**, using the piece's
position seen by the camera.

> This module reflects what the system **actually uses**. There is **no ArUco**,
> no printed markers, no reference-point capture. That was removed as it is not
> part of the real pipeline.

## The idea in one sentence

> Wherever the piece is → drive the robot there → save the joint angles → train.
> Then, for any new piece position, interpolate the joints.

## Two pieces of the puzzle

```
 camera pixel (cx,cy)
        │  homography.npy      (fixed camera→table calibration)
        ▼
 table position (x_mm, y_mm)
        │  pick_model.json     (learned position→joints, IDW)
        ▼
 6 joint angles  →  robot moves & picks
```

1. **Homography** (`homography.npy` + `homography_utils.py`)
   A fixed 3×3 matrix that converts a camera pixel into a table coordinate in mm.
   It only needs to give a *stable, repeatable* coordinate — the pick model
   handles the rest. It is calibrated once and shipped here.

2. **Pick model — the dynamic part you build** (`pick_model.json` + `pick_model.py`)
   A list of `(x_mm, y_mm) → 6 joints` samples you teach by hand. For a new
   position it uses **inverse-distance weighting (IDW)**: closer taught points
   have more influence. No inverse-kinematics solver needed.

## Files (only what's used)

| File | Role |
|------|------|
| `calibrate_pick.py` | **The exercise.** Detect piece → jog robot → save joints → build `pick_model.json`. |
| `pick_model.py` | `get_pick_joints(x_mm, y_mm)` — position → joints via IDW. |
| `pick_model.json` | The learned samples (the "trained" pick model). |
| `homography_utils.py` | `pixel_to_robot()` — the pixel→mm transform. |
| `homography.npy` | The fixed pixel→mm calibration (real data from the cell). |
| `calib_pairs.json` | Raw calibration samples (pixels, mm, joints). |
| `config.py` | Module settings (camera, files, topics). |
| `define_zone.py` | Draw the robot's reachable area → `zone.json`. |
| `detector_node.py` | ROS 2 node: YOLO + homography → publish piece position. |
| `pick_node.py` | ROS 2 node: read position → IDW joints → move arm + vacuum. |
| `launch_detector.sh` / `launch_pick.sh` | Source ROS 2 and run each node. |

## The exercise: build the dynamic pick model

Needs ROS 2 sourced (to read the robot's joints).

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
python3 calibrate_pick.py
```

For each of ~6+ pieces spread across the belt:
1. Put a piece down — YOLO shows its position.
2. Press **SPACE** to capture it.
3. **Jog the robot tip onto the piece**; the script reads `/robot2/joint_states`.
4. Repeat.
5. Press **Q** → it writes `pick_model.json` (and `calib_pairs.json`).

That's the whole "training": you are teaching a handful of real poses, and IDW
fills in everything between them.

### Test the model without a robot
```bash
python3 pick_model.py     # prints interpolated joints for sample positions
```

## Collecting more / better data
- Spread calibration points across the **whole reachable area** (corners matter).
- If picks are slightly off in one region, add a few points there and re-run.
- **Never move the camera** after calibrating — the homography is tied to its pose.

## Starting the robot (full startup sequence)

The Niryo Ned is not driven directly — a ROS 2 **driver** bridges to it over the
network. You must bring that up **before** any node that moves the arm
(`calibrate_pick.py`, `pick_node.py`).

### 0. Physical / network
- Power on the robot and wait until it is ready.
- Make sure it is reachable from the control PC (know its hostname, e.g.
  `ned2-aa-bbb-ccc.local`, or its IP). Test: `ping <robot-host>`.

### 1. Source ROS 2 and the workspace
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

### 2. Tell the driver which robot to connect to
Edit the driver's robot list (or a copy of it):
`~/ros2_ws/src/ned-ros2-driver/niryo_ned_ros2_driver/config/drivers_list.yaml`
```yaml
rosbridge_port: 9090
robot_namespaces:
  - "robot2"                     # this is why topics live under /robot2/...
robot_ips:
  - "ned2-aa-bbb-ccc.local"      # <-- your robot's hostname or IP
```

### 3. Launch the driver
```bash
ros2 launch niryo_ned_ros2_driver driver.launch.py
# or with a custom file:
ros2 launch niryo_ned_ros2_driver driver.launch.py drivers_list_file:=/path/to/drivers_list.yaml
```

### 4. Verify the robot is up
```bash
ros2 node list                       # expect /ros2_driver_robot2
ros2 topic list | grep robot2        # /robot2/joint_states, .../robot_action, ...
ros2 topic echo --once /robot2/joint_states   # should print 6 joint values
```

### 5. Run the vision + pick (each in its own terminal, ROS 2 sourced)
```bash
python3 define_zone.py     # once: draw the reachable area -> zone.json
./launch_detector.sh       # terminal A: publishes /robot2/piece_detected
./launch_pick.sh           # terminal B: picks whatever is published
```
And to (re)build the pick model: `python3 calibrate_pick.py` (see above).

> The joint poses (`JOINTS`) and `VACUUM_ID` in `pick_node.py` are specific to
> the original Niryo cell — re-teach them for your robot.
> If a node hangs on "waiting for action server", the driver (step 3) is not
> running or the namespace/IP in `drivers_list.yaml` is wrong.
