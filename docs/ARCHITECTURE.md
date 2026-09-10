# Architecture

A teaching walk-through of how the whole vision → robot → database pipeline fits
together, and where each module sits.

## The cell

- **4 conveyor belts** (`conveyor1`..`conveyor4`), each watched by one camera.
- **2 Logitech C920 webcams** provide those views (each exposes 2 `/dev/video`
  nodes, but only the even ones carry images — see module 01).
- A **Niryo Ned robot** (`/robot2`) with a **vacuum gripper** picks pieces off
  one belt (`conveyor2`).
- A **PostgreSQL** database records what the cameras see.
- A **factory supervisor** (another computer) publishes context on `/factory/*`.

## Layered view

```
┌──────────────────────────────────────────────────────────────────────┐
│  01 Cameras        detect + assign index -> zone           config.py   │
├──────────────────────────────────────────────────────────────────────┤
│  02 ROIs           name the regions each camera cares about  rois.json │
├──────────────────────────────────────────────────────────────────────┤
│  03 Dataset        capture images to train YOLO                        │
├──────────────────────────────────────────────────────────────────────┤
│  04 Conveyor ML    moving/stopped per belt (optical flow + sklearn)    │
├──────────────────────────────────────────────────────────────────────┤
│  05 Robot coords   pixel -> mm (homography) -> joints (IDW) -> pick    │
├──────────────────────────────────────────────────────────────────────┤
│  06 Integration    ROS 2 topics + PostgreSQL logging                   │
└──────────────────────────────────────────────────────────────────────┘
```

## Two independent vision jobs

The kit really does two different things with the cameras:

1. **Object detection (YOLO)** — *what piece is where*. Used for the robot pick
   (module 05) and for logging belt contents (module 06).
2. **Motion detection (optical flow)** — *is the belt moving*. Used to verify
   the belts behave as the supervisor expects (module 04).

They share the cameras and the ROIs but are otherwise separate models.

## Runtime processes

```
                        ┌───────────────────────────┐
  /factory/system_state │      vision_logger        │  PostgreSQL
  /factory/run_id ─────▶│  (module 06)              │──────────▶ snapshots
                        │  YOLO + ROIs + motion     │──▶ vision/conveyor_state
                        └───────────────────────────┘

  ┌──────────────────┐   /robot2/piece_detected   ┌──────────────────┐
  │  detector_node   │──────────────────────────▶ │   pick_node      │──▶ robot
  │  (module 05)     │      {type,x_mm,y_mm}       │  (module 05)     │    (vacuum)
  │  YOLO+homography │                             │  IDW joints      │
  └──────────────────┘                             └──────────────────┘
```

## The coordinate chain (module 05, the key idea)

```
 pixel (cx,cy)  ──H (homography.npy)──▶  robot mm (x,y)  ──IDW (pick_model.json)──▶  6 joints
```

- **H** is found once during calibration and is only valid while the camera
  stays put.
- **IDW** interpolates joint angles from a few taught poses, so no inverse
  kinematics solver is needed.

## Suggested learning order

1. `01_cameras` — find and assign cameras.
2. `02_rois` — draw the regions.
3. `03_dataset` + train YOLO (external) — or reuse `best.pt`.
4. `04_conveyor_training` — teach moving/stopped.
5. `05_robot_coordinates` — calibrate and pick.
6. `06_system_integration` — wire it into topics + DB.
