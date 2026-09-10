# Module 01 — Cameras

Goal: know exactly **which cameras you have**, **what index each one is**, and
**assign each index to a zone**.

## Scripts

| Script | What it does |
|--------|--------------|
| `detect_cameras.py` | Lists physical cameras, their `/dev/videoN` nodes, and tells apart real image streams from metadata nodes. Recommends the indices to use. |
| `view_cameras.py` | Opens the cameras live in a grid, each tile labelled with its index and assigned zone. Confirm the wiring visually. |

## The one thing to understand: metadata nodes

A USB webcam like the Logitech C920 creates **two** `/dev/video` nodes:

- `/dev/video0`, `/dev/video2`, … (even) → **the real image**
- `/dev/video1`, `/dev/video3`, … (odd) → **UVC metadata** (opens, but no useful picture)

So two physical webcams look like *four* devices. `detect_cameras.py` reads the
V4L2 capabilities of each node and marks the metadata ones as `skip`.

## Workflow

```bash
# 1. Discover the real indices
python3 detect_cameras.py

# 2. Look at them live and see which belt is which
python3 view_cameras.py

# 3. Edit the mapping in ../config.py
#    CAMERA_ZONES = { 0: "conveyor4", 2: "conveyor3", 4: "conveyor2", 6: "conveyor1" }
```

## Assigning "camera 0 → zone 1"

That assignment is **just a dictionary** in [`../config.py`](../config.py):

```python
CAMERA_ZONES = {
    0: "conveyor4",   # camera at index 0 watches belt 4
    2: "conveyor3",
    4: "conveyor2",
    6: "conveyor1",
}
```

Every other module imports this map, so you change the wiring in one place only.
