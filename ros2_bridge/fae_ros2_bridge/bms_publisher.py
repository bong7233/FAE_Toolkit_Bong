"""ROS 2 node: publish BMS telemetry as sensor_msgs/BatteryState.

Builds on :class:`fae_toolkit.bridge.BmsTelemetrySource`, so it works against a
real serial port or the built-in simulator (when no ``port`` parameter is set).

Parameters:
    port (str):      serial port; empty string uses the simulator (default).
    unit_id (int):   Modbus unit id (default 1).
    rate_hz (float): publish rate (default 2.0).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState

from fae_toolkit.bridge import BmsTelemetrySource


class BmsPublisher(Node):
    def __init__(self) -> None:
        super().__init__("fae_bms_publisher")
        self.declare_parameter("port", "")
        self.declare_parameter("unit_id", 1)
        self.declare_parameter("rate_hz", 2.0)

        port = self.get_parameter("port").get_parameter_value().string_value or None
        unit_id = self.get_parameter("unit_id").get_parameter_value().integer_value
        rate_hz = self.get_parameter("rate_hz").get_parameter_value().double_value

        self._source = BmsTelemetrySource(port=port, unit_id=unit_id)
        self._pub = self.create_publisher(BatteryState, "bms/state", 10)
        self._timer = self.create_timer(1.0 / max(rate_hz, 0.1), self._tick)
        self.get_logger().info(f"FAE BMS publisher started (port={port or 'simulator'})")

    def _tick(self) -> None:
        try:
            telemetry = self._source.read()
        except Exception as exc:  # keep the node alive on a comm hiccup
            self.get_logger().warn(f"BMS read failed: {exc}")
            return
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = float(telemetry.pack_voltage)
        msg.current = float(telemetry.pack_current)
        msg.percentage = float(telemetry.soc / 100.0)
        msg.temperature = float(telemetry.max_temp)
        msg.present = True
        self._pub.publish(msg)

    def destroy_node(self) -> bool:
        self._source.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BmsPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
