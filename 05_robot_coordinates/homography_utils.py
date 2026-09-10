"""
homography_utils.py - convert image pixels to robot mm using the homography H.

A homography is a 3x3 matrix that maps points on one plane to another plane,
correcting perspective. Here it maps camera pixels (px, py) to robot table
coordinates (x_mm, y_mm):

    [x']   [ h11 h12 h13 ] [px]
    [y'] = [ h21 h22 h23 ] [py]
    [w ]   [ h31 h32 h33 ] [ 1]

    x_mm = x' / w ,  y_mm = y' / w      (homogeneous normalization)
"""

import numpy as np
from pathlib import Path

_H = None   # module-level cache


def load_homography(path=None) -> np.ndarray:
    global _H
    if _H is not None:
        return _H
    if path is None:
        from config import HOMOGRAPHY_FILE
        path = HOMOGRAPHY_FILE
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Homography not found: {path}. It ships with the kit; "
            f"calibrate_pick.py also refreshes it.")
    _H = np.load(str(path))
    return _H


def pixel_to_robot(px: float, py: float, H: np.ndarray = None):
    """Map one pixel point to robot (x_mm, y_mm)."""
    if H is None:
        H = load_homography()
    pt = H @ np.array([px, py, 1.0])
    pt /= pt[2]
    return float(pt[0]), float(pt[1])
