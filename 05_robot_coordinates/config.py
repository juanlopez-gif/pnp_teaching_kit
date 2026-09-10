"""
config.py (module 05) - parameters for the dynamic robot pick.

What this module really uses (verified against the production code):
  - homography.npy      : fixed camera-pixel -> table-mm mapping
  - pick_model.json     : mm -> 6 robot joints (IDW interpolation)
  - calibrate_pick.py   : builds pick_model.json (detect piece, jog robot, save joints)

There is NO ArUco / marker / reference-point step in the real system.
"""

import importlib.util
from pathlib import Path

# Pull shared settings from the kit-wide config (camera index, model path).
# Loaded by absolute path so it never clashes with this module (also "config").
_kit_cfg_path = Path(__file__).resolve().parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("kit_config", _kit_cfg_path)
kit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit)  # noqa: E402

# ── Camera ───────────────────────────────────────────────────────────────────────
# The camera overlooking the belt the robot picks from.
CAMERA_ID = kit.ROBOT_CAMERA_INDEX
FRAME_W   = kit.FRAME_WIDTH
FRAME_H   = kit.FRAME_HEIGHT

# ── Files ──────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
HOMOGRAPHY_FILE = BASE_DIR / "homography.npy"     # pixel -> mm (fixed calibration)
PICK_MODEL_FILE = BASE_DIR / "pick_model.json"    # mm -> joints (IDW model)
CALIB_FILE      = BASE_DIR / "calib_pairs.json"   # raw calibration samples
ZONE_FILE       = BASE_DIR / "zone.json"          # robot actuation area

# YOLO piece detector (shared with the rest of the kit).
YOLO_MODEL_PATH = kit.YOLO_MODEL_PATH
CONF_THRESH     = kit.CONF_THRESHOLD

# ── ROS 2 topics (shared) ──────────────────────────────────────────────────────
ROBOT2_ACTION   = kit.ROBOT2_ACTION
PIECE_TOPIC_OUT = kit.PIECE_TOPIC_OUT
