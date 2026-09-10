"""
pick_node.py - ROS 2 node: consume detections and execute a vacuum pick.

Sequence
--------
  1. A piece appears on PIECE_TOPIC_OUT while idle -> HOME -> at_capture pose
  2. From the capture pose, grab a FRESH (x_mm, y_mm) reading
  3. IDW pick_model -> prepick_joints, pick_joints
  4. prepick -> pick -> vacuum PULL -> prepick -> HOME -> vacuum PUSH (drop)

Interfaces
----------
  sub   PIECE_TOPIC_OUT                            std_msgs/String
  act   /robot2/niryo_robot_arm_commander/robot_action   niryo .../RobotMove
  srv   /robot2/niryo_robot/tools/pull_air_vacuum_pump   niryo .../ToolCommand
  srv   /robot2/niryo_robot/tools/push_air_vacuum_pump   niryo .../ToolCommand

NOTE: the JOINTS poses and VACUUM_ID below are specific to one robot/cell.
Re-teach them for your setup (calibrate_pick.py builds pick_model.json).
"""
import sys
import json
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PIECE_TOPIC_OUT
from pick_model import get_pick_joints

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String

from niryo_ned_ros2_interfaces.action import RobotMove
from niryo_ned_ros2_interfaces.msg import ArmMoveCommand
from niryo_ned_ros2_interfaces.srv import ToolCommand

VACUUM_ID = 31
COORD_TIMEOUT = 8.0

# Named joint poses (cell-specific - re-teach for your robot).
JOINTS = {
    "home":            [-0.0007,  0.4994, -1.2506,  0.0001,  0.0014, -0.0030],
    "at_capture_c2s2": [-1.7631, -0.1747, -0.7068, -0.1150, -0.9558, -1.1581],
}


def _wait(future):
    done = threading.Event()
    future.add_done_callback(lambda _: done.set())
    done.wait()
    return future.result()


class PickNode(Node):
    def __init__(self):
        super().__init__("robot2_pick_node")
        cb = ReentrantCallbackGroup()
        self._action = ActionClient(self, RobotMove,
                                    "/robot2/niryo_robot_arm_commander/robot_action",
                                    callback_group=cb)
        self._pull = self.create_client(ToolCommand,
                                        "/robot2/niryo_robot/tools/pull_air_vacuum_pump",
                                        callback_group=cb)
        self._push = self.create_client(ToolCommand,
                                        "/robot2/niryo_robot/tools/push_air_vacuum_pump",
                                        callback_group=cb)
        self._sub = self.create_subscription(String, PIECE_TOPIC_OUT,
                                             self._on_detection, 10, callback_group=cb)
        self._busy = False
        self._lock = threading.Lock()
        self._waiting_coords = False
        self._coord_event = threading.Event()
        self._coord_data = None
        self.get_logger().info("pick_node ready. Waiting for detections...")

    def _on_detection(self, msg: String):
        data = json.loads(msg.data)
        if self._waiting_coords:
            self._coord_data = data
            self._coord_event.set()
            return
        with self._lock:
            if self._busy:
                return
            self._busy = True
        self.get_logger().info(f"[PICK] Trigger - {data['type']} conf={data['conf']:.2f}")
        threading.Thread(target=self._sequence, daemon=True).start()

    def _sequence(self):
        try:
            self._move("home")
            self._move("at_capture_c2s2")

            time.sleep(0.4)
            self._coord_data = None
            self._coord_event.clear()
            self._waiting_coords = True
            got = self._coord_event.wait(timeout=COORD_TIMEOUT)
            self._waiting_coords = False

            if not got or self._coord_data is None:
                self.get_logger().warn("[PICK] Timeout waiting for detection. Aborting.")
                self._move("home")
                return

            x_mm, y_mm = self._coord_data["x_mm"], self._coord_data["y_mm"]
            self.get_logger().info(f"[PICK] ({x_mm:.1f}, {y_mm:.1f}) mm -> IDW model")

            pick_j, prepick_j = get_pick_joints(x_mm, y_mm)
            self._move_joints(prepick_j, "prepick")
            self._move_joints(pick_j, "pick")
            self._vacuum("pull")
            self._move_joints(prepick_j, "prepick_retract")
            self._move("home")
            self._vacuum("push")
            self.get_logger().info("[PICK] Done.")
        except Exception as e:
            self.get_logger().error(f"[PICK] Error: {e}")
        finally:
            with self._lock:
                self._busy = False

    def _move(self, name: str):
        self.get_logger().info(f"  -> {name}")
        cmd = ArmMoveCommand()
        cmd.cmd_type = ArmMoveCommand.JOINTS
        cmd.joints = [float(j) for j in JOINTS[name]]
        self._send_move(cmd)

    def _move_joints(self, joints: list, label: str = ""):
        self.get_logger().info(f"  -> joints [{label}]")
        cmd = ArmMoveCommand()
        cmd.cmd_type = ArmMoveCommand.JOINTS
        cmd.joints = [float(j) for j in joints]
        self._send_move(cmd)

    def _send_move(self, cmd: ArmMoveCommand) -> bool:
        goal = RobotMove.Goal()
        goal.cmd = cmd
        self._action.wait_for_server()
        handle = _wait(self._action.send_goal_async(goal))
        if not handle.accepted:
            return False
        result = _wait(handle.get_result_async()).result
        return result.status >= 1

    def _vacuum(self, action: str):
        self.get_logger().info(f"  -> vacuum {action.upper()}")
        req = ToolCommand.Request()
        req.id = VACUUM_ID
        if action == "pull":
            req.position, req.max_torque, req.hold_torque = 0, 1000, 800
            cli = self._pull
        else:
            req.position, req.max_torque, req.hold_torque = 1900, -1000, 0
            cli = self._push
        cli.wait_for_service()
        _wait(cli.call_async(req))


def main():
    rclpy.init()
    node = PickNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
