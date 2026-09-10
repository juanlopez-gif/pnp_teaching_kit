"""
pick_model.py - Inverse-Distance-Weighting (IDW) interpolation of pick joints.

Given a target (x_mm, y_mm), return the 6 robot joint angles that place the tool
on that point, plus the "prepick" (approach) joints. No inverse-kinematics
service required: it interpolates between calibrated (position -> joints) samples
stored in pick_model.json.

Why joints and not just XY?
  The homography gives you WHERE the piece is (mm). To actually reach it you
  need joint angles. Instead of solving IK, we teach the robot a handful of
  real poses during calibration and interpolate between them.
"""
import json
import math
from pathlib import Path

_MODEL_PATH = Path(__file__).resolve().parent / "pick_model.json"
_model = None


def _load():
    global _model
    if _model is None:
        _model = json.loads(_MODEL_PATH.read_text())
    return _model


def get_pick_joints(x_mm: float, y_mm: float, power: float = 2.0):
    """
    Return (pick_joints, prepick_joints) for target (x_mm, y_mm).

    If the target lands exactly on a calibrated point, those joints are used.
    delta_prepick (joints 1..5) is added the same way for any position.
    """
    m = _load()
    pts = m["points"]
    dp = m["delta_prepick"]                # delta for joint indices 1..5

    dists = [math.hypot(x_mm - p["x_mm"], y_mm - p["y_mm"]) for p in pts]

    # Exact match shortcut.
    for i, d in enumerate(dists):
        if d < 0.1:
            pj = list(pts[i]["pick_joints"])
            return pj, _apply_prepick_delta(pj, dp)

    # Inverse-distance weighting.
    weights = [1.0 / (d ** power) for d in dists]
    total = sum(weights)
    n_joints = len(pts[0]["pick_joints"])
    pick_joints = [
        sum(weights[i] * pts[i]["pick_joints"][j] for i in range(len(pts))) / total
        for j in range(n_joints)
    ]
    return pick_joints, _apply_prepick_delta(pick_joints, dp)


def _apply_prepick_delta(pick_j: list, dp: list) -> list:
    """Add the prepick delta (joints 1..5) to the pick joints."""
    pre = list(pick_j)
    for k, delta in enumerate(dp):
        pre[k + 1] += delta
    return pre


if __name__ == "__main__":
    for x, y in [(-21.0, -257.0), (-55.0, -293.0), (-50.0, -280.0)]:
        pick, prepick = get_pick_joints(x, y)
        print(f"({x:6.1f},{y:7.1f})")
        print("  pick   :", [round(v, 4) for v in pick])
        print("  prepick:", [round(v, 4) for v in prepick])
