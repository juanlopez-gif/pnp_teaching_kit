#!/usr/bin/env python3
"""
Step 1 - Detect the cameras.
============================

Answers three questions:
  1. Which physical cameras are connected, and what are they called?
  2. Which /dev/videoN nodes are REAL image streams vs. metadata nodes?
  3. Which index should I put in config.CAMERA_ZONES?

Why this matters
----------------
A single USB webcam (e.g. Logitech C920) often exposes TWO /dev/video nodes:
  - an EVEN node  -> the actual video (what you want)
  - an ODD node   -> UVC metadata (opens fine, but is useless for images)
OpenCV will happily "open" both, so a naive scan reports twice as many
cameras as you really have. This script cross-checks the V4L2 capabilities
to tell them apart.

Usage
-----
    python3 detect_cameras.py
"""

import re
import subprocess

import cv2


# ── V4L2 helpers ────────────────────────────────────────────────────────────────

def run_v4l2(args):
    """Run a v4l2-ctl command; return stdout or None if the tool is missing."""
    try:
        out = subprocess.run(["v4l2-ctl", *args],
                             capture_output=True, text=True, timeout=5)
        return out.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def list_devices():
    """
    Parse `v4l2-ctl --list-devices` into {camera_name: [/dev/videoN, ...]}.
    """
    text = run_v4l2(["--list-devices"])
    devices = {}
    if not text:
        return devices
    current = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line.startswith("\t"):            # header line = camera name
            current = line.strip().rstrip(":")
            devices[current] = []
        elif current is not None:                # indented = a node path
            node = line.strip()
            if node.startswith("/dev/video"):
                devices[current].append(node)
    return devices


def is_real_capture_node(node):
    """
    True if /dev/videoN advertises 'Video Capture' (not just 'Metadata Capture').
    Falls back to True if v4l2-ctl is unavailable (we cannot tell, so keep it).
    """
    info = run_v4l2(["-d", node, "--all"])
    if info is None:
        return True
    # The 'Device Caps' block lists the capabilities of this specific node.
    caps_block = info.split("Device Caps")[-1] if "Device Caps" in info else info
    return "Video Capture" in caps_block


def node_index(node):
    """/dev/video3 -> 3"""
    m = re.search(r"(\d+)$", node)
    return int(m.group(1)) if m else None


# ── OpenCV probe ────────────────────────────────────────────────────────────────

def probe_opencv(index):
    """Open a camera index with OpenCV and read one frame. Returns info dict or None."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return None
    info = {
        "index": index,
        "width":  int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps":    cap.get(cv2.CAP_PROP_FPS),
    }
    ok, frame = cap.read()
    info["readable"] = bool(ok and frame is not None)
    cap.release()
    return info


# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CAMERA DETECTION")
    print("=" * 60)

    devices = list_devices()

    if devices:
        print("\n[V4L2] Physical cameras detected:\n")
        real_indices = []
        for name, nodes in devices.items():
            print(f"  {name}")
            for node in nodes:
                idx = node_index(node)
                real = is_real_capture_node(node)
                tag = "IMAGE" if real else "metadata (skip)"
                idx_str = f"index {idx}" if idx is not None else "n/a"
                print(f"     {node:<16} {idx_str:<10} -> {tag}")
                if real and idx is not None:
                    real_indices.append(idx)
            print()
    else:
        print("\n[V4L2] v4l2-ctl not available — using OpenCV probing only.\n")
        real_indices = None   # unknown; probe everything below

    # OpenCV confirmation: open each candidate index and read a frame.
    print("[OpenCV] Verifying that indices actually deliver frames...\n")
    candidates = real_indices if real_indices is not None else range(10)
    working = []
    for idx in sorted(set(candidates)):
        info = probe_opencv(idx)
        if info is None:
            continue
        working.append(info)
        status = "OK" if info["readable"] else "opens but no frame"
        print(f"  index {info['index']:>2} | {info['width']}x{info['height']} "
              f"@ {info['fps']:.0f} fps | {status}")

    if not working:
        print("No usable cameras found.")
        return

    good = [c["index"] for c in working if c["readable"]]
    print("\n" + "-" * 60)
    print("Recommended capture indices (edit config.CAMERA_ZONES):")
    print(f"    {good}")
    print("\nNext: run  view_cameras.py  to see which physical camera is which,")
    print("then assign each index to a zone in config.py.")
    print("=" * 60)


if __name__ == "__main__":
    main()
