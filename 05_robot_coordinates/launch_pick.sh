#!/bin/bash
# Launch the pick node (subscribes to /robot2/piece_detected, moves the robot).
source /opt/ros/jazzy/setup.bash
source "$HOME/ros2_ws/install/setup.bash"

KIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"   # machine_learning_model_19_04
VENV_PY="$KIT_DIR/venv/bin/python"

PYTHONPATH=/opt/ros/jazzy/lib/python3.12/site-packages:$HOME/ros2_ws/install/niryo_ned_ros2_interfaces/lib/python3.12/site-packages:$PYTHONPATH \
  "$VENV_PY" "$(dirname "$0")/pick_node.py"
