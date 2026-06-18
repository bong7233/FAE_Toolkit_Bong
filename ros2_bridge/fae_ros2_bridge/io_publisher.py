"""ROS 2 node: publish IO/interlock state to topics.

Publishes:
    io/interlock_ok  (std_msgs/Bool)    — safe to actuate
    io/distance_mm   (std_msgs/Float32) — proximity analog input

Builds on :class:`fae_toolkit.bridge.IoTelemetrySource` (real port or simulator).
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32

from fae_toolkit.bridge import IoTelemetrySource
from fae_toolkit.protocols.io import io_map


class IoPublisher(Node):
    def __init__(self) -> None:
        super().__init__("fae_io_publisher")
        self.declare_parameter("port", "")
        self.declare_parameter("unit_id", 1)
        self.declare_parameter("rate_hz", 5.0)

        port = self.get_parameter("port").get_parameter_value().string_value or None
        unit_id = self.get_parameter("unit_id").get_parameter_value().integer_value
        rate_hz = self.get_parameter("rate_hz").get_parameter_value().double_value

        self._source = IoTelemetrySource(port=port, unit_id=unit_id)
        self._pub_interlock = self.create_publisher(Bool, "io/interlock_ok", 10)
        self._pub_distance = self.create_publisher(Float32, "io/distance_mm", 10)
        self._timer = self.create_timer(1.0 / max(rate_hz, 0.1), self._tick)
        self.get_logger().info(f"FAE IO publisher started (port={port or 'simulator'})")

    def _tick(self) -> None:
        try:
            snapshot = self._source.read()
        except Exception as exc:
            self.get_logger().warn(f"IO read failed: {exc}")
            return
        self._pub_interlock.publish(Bool(data=bool(snapshot.interlock_ok)))
        self._pub_distance.publish(Float32(data=float(snapshot.ai[io_map.AI_DISTANCE])))

    def destroy_node(self) -> bool:
        self._source.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = IoPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
