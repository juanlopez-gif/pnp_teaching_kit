# ROS 2 topics & interfaces

Every topic/action/service the kit uses. Topic name constants live in
[`../config.py`](../config.py) so code and docs stay in sync.

## Naming
The robot lives under the `/robot2/...` namespace. Factory-wide topics live
under `/factory/...`. ROS 2 distro: **Jazzy** (Python 3.12).

## Piece detection (module 05)

| Topic | Type | Dir | Node | Payload |
|-------|------|-----|------|---------|
| `/robot2/piece_detected` | `std_msgs/String` | pub | `detector_node.py` | `{"type","conf","x_mm","y_mm"}` (JSON) |
| `/robot2/piece_detected` | `std_msgs/String` | sub | `pick_node.py` | same |

### Robot motion (module 05, `pick_node.py`)

| Interface | Type | Kind |
|-----------|------|------|
| `/robot2/niryo_robot_arm_commander/robot_action` | `niryo_ned_ros2_interfaces/action/RobotMove` | action client |
| `/robot2/niryo_robot/tools/pull_air_vacuum_pump` | `niryo_ned_ros2_interfaces/srv/ToolCommand` | service client (grab) |
| `/robot2/niryo_robot/tools/push_air_vacuum_pump` | `niryo_ned_ros2_interfaces/srv/ToolCommand` | service client (release) |
| `/robot2/joint_states` | `sensor_msgs/JointState` | read via `ros2 topic echo` during calibration |

The `RobotMove` goal carries an `ArmMoveCommand` with `cmd_type = JOINTS` and a
6-value `joints` list (this cell drives the arm in joint space, not Cartesian).

## System integration (module 06)

| Topic | Type | Dir | Purpose |
|-------|------|-----|---------|
| `/factory/run_id` | `std_msgs/String` | sub | current production run id (latched QoS) |
| `/factory/system_state` | `std_msgs/String` | sub | master JSON: expected pieces, robot states, block logic |
| `/factory/conveyor_1/status` | `std_msgs/String` | sub | expected RUNNING/STOPPED for belt 1 |
| `/factory/conveyor_2/status` | `std_msgs/String` | sub | expected RUNNING/STOPPED for belt 2 |
| `/niryo_factory/status` | `std_msgs/String` | sub | triggers dynamic pick-joint computation |
| `vision/conveyor_state` | `std_msgs/String` | pub | (reference node) detected content per belt |
| `stack_status` | `std_msgs/String` | pub | (production) live 3×6 stack state |
| `/robot2/pick_joints_c2s2` | `std_msgs/String` | pub | (production) computed pick/prepick joints + mm |

## Data flow summary

```
                 ┌───────────────────────── /factory/system_state, run_id ─────────┐
                 ▼                                                                   │
  cameras ─▶ YOLO ─▶ ROIs ─▶ vision_logger ─▶ PostgreSQL + vision/conveyor_state    │
                                                                                     │
  pick camera ─▶ detector_node ─▶ /robot2/piece_detected ─▶ pick_node ─▶ RobotMove  │
                    (homography)                              (IDW joints, vacuum)   │
```

## Handy commands

```bash
ros2 topic list
ros2 topic echo /robot2/piece_detected
ros2 topic hz   /robot2/piece_detected
ros2 topic echo --once /robot2/joint_states      # used during calibration
ros2 node list
```
