"""
config.py — Single source of truth for the teaching kit.
================================================================

Everything that depends on "which camera watches which part of the cell"
lives here so you only edit it in ONE place. Every script in the kit
imports from this file.

WORKFLOW TO ADAPT THIS FILE TO YOUR SETUP
-----------------------------------------
1. Run  01_cameras/detect_cameras.py   -> find the real capture indices.
2. Run  01_cameras/view_cameras.py     -> confirm which physical camera
                                          is at each index (watch the live feed).
3. Edit CAMERA_ZONES below so each index points at the correct zone.

That is the whole "assign camera 0 to zone 1" idea: it is just a
dictionary you edit.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
# Root of the teaching kit (this file's folder).
KIT_DIR = Path(__file__).resolve().parent

# The trained YOLO object-detection weights (pieces on the belts).
# Point this at your .pt file. By default we reuse the one from the parent project.
YOLO_MODEL_PATH = KIT_DIR.parent / "best.pt"

# Shared ROI polygons file (named regions per camera). Written by 02_rois.
ROIS_PATH = KIT_DIR / "02_rois" / "rois.json"

# ── Camera capture defaults ─────────────────────────────────────────────────────
FRAME_WIDTH  = 640
FRAME_HEIGHT = 480

# ── Camera <-> zone assignment ──────────────────────────────────────────────────
# THE key table. Map each V4L2 capture index to the logical zone it observes.
# Change these numbers to match YOUR wiring (see detect_cameras.py output).
#
# In this cell there are 4 belts. Two Logitech C920 webcams expose two /dev/video
# nodes each, but only the EVEN nodes (0 and 2) are real image streams — the odd
# nodes (1, 3) are metadata. detect_cameras.py explains this.
CAMERA_ZONES = {
    0: "conveyor4",
    2: "conveyor3",
    4: "conveyor2",
    6: "conveyor1",
}

# Convenience reverse lookup: zone name -> camera index.
ZONE_CAMERAS = {zone: idx for idx, zone in CAMERA_ZONES.items()}

# The camera used for robot pixel->mm coordinate work (module 05).
# It must be the one that overlooks the belt the robot picks from.
ROBOT_CAMERA_INDEX = ZONE_CAMERAS.get("conveyor2", 4)

# ── Per-zone conveyor motion models (module 04) ─────────────────────────────────
# Each belt gets its own trained "moving / stopped" model directory.
CONVEYOR_MODEL_DIRS = {
    "conveyor1": KIT_DIR / "04_conveyor_training" / "models" / "conveyor1",
    "conveyor2": KIT_DIR / "04_conveyor_training" / "models" / "conveyor2",
    "conveyor3": KIT_DIR / "04_conveyor_training" / "models" / "conveyor3",
    "conveyor4": KIT_DIR / "04_conveyor_training" / "models" / "conveyor4",
}

# ── Detection ───────────────────────────────────────────────────────────────────
CONF_THRESHOLD = 0.45     # minimum YOLO confidence to accept a piece

# ── ROS 2 topics (module 05 + 06) ───────────────────────────────────────────────
# Kept here so documentation and code never drift apart.
PIECE_TOPIC_OUT     = "/robot2/piece_detected"          # std_msgs/String (JSON)
ROBOT2_ACTION       = "/robot2/niryo_robot_arm_commander/robot_action"
PICK_JOINTS_TOPIC   = "/robot2/pick_joints_c2s2"        # std_msgs/String (JSON)

# ── Database (module 06) ────────────────────────────────────────────────────────
# All values are overridable with the standard PG* environment variables.
import os
DB_HOST     = os.environ.get("PGHOST",     "127.0.0.1")
DB_PORT     = int(os.environ.get("PGPORT",  "5432"))
DB_USER     = os.environ.get("PGUSER",     "twin_mes_db")
DB_PASSWORD = os.environ.get("PGPASSWORD", "postgres")
DB_NAME     = os.environ.get("PGDATABASE", "twin_mes_db")
DB_SCHEMA   = os.environ.get("PGSCHEMA",   "shipyard_pnp_ws")
