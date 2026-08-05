from setuptools import find_packages, setup

PACKAGE = "de4sdv_vehicle_speed_tcp_bridge"

setup(
    name=PACKAGE,
    version="0.1.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="DE4SDV maintainers",
    maintainer_email="maintainers@de4sdv.org",
    description="AAOS Vehicle.Speed TCP-to-Autoware transfer bench.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "vehicle_speed_tcp_bridge = de4sdv_vehicle_speed_tcp_bridge.node:main",
            "observe_velocity_report = de4sdv_vehicle_speed_tcp_bridge.observer:main",
        ]
    },
)
