# fae_ros2_bridge

A ROS 2 (`ament_python`) package that publishes FAE Toolkit telemetry to ROS 2
topics — so the toolkit's battery/IO data can flow into a ROS 2 robot stack.
Linux-only, as ROS 2 is Linux-first.

Each node builds on `fae_toolkit.bridge`, which works against a **real serial
port or the built-in simulator** (no hardware needed for a demo).

## Nodes / topics

| Node | Topic | Type |
|------|-------|------|
| `bms_publisher` | `bms/state` | `sensor_msgs/BatteryState` |
| `io_publisher`  | `io/interlock_ok` | `std_msgs/Bool` |
| `io_publisher`  | `io/distance_mm`  | `std_msgs/Float32` |

## Build (colcon)

```bash
# from a ROS 2 environment (e.g. Humble), with the toolkit installed:
pip install -e .                       # installs fae_toolkit (repo root)

mkdir -p ~/ros2_ws/src
ln -s "$PWD/ros2_bridge" ~/ros2_ws/src/fae_ros2_bridge
cd ~/ros2_ws
colcon build --packages-select fae_ros2_bridge
source install/setup.bash
```

## Run (against the simulator)

```bash
ros2 run fae_ros2_bridge bms_publisher
# in another terminal:
ros2 topic echo /bms/state

# IO interlock + proximity:
ros2 run fae_ros2_bridge io_publisher
ros2 topic echo /io/interlock_ok
```

To use real hardware instead of the simulator, pass the serial port:

```bash
ros2 run fae_ros2_bridge bms_publisher --ros-args -p port:=/dev/ttyUSB0
```
