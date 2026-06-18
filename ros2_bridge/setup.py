from setuptools import find_packages, setup

package_name = "fae_ros2_bridge"

setup(
    name=package_name,
    version="0.2.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Sangbong Lee",
    maintainer_email="batmantwo7233@gmail.com",
    description="Publishes FAE Toolkit BMS/IO telemetry to ROS 2 topics.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "bms_publisher = fae_ros2_bridge.bms_publisher:main",
            "io_publisher = fae_ros2_bridge.io_publisher:main",
        ],
    },
)
