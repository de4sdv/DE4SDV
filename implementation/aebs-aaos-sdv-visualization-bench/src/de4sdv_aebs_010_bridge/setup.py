from setuptools import find_packages, setup

package_name = "de4sdv_aebs_010_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/de4sdv_aebs_010_bridge"]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="DE4SDV maintainers",
    maintainer_email="de4sdv@example.invalid",
    description="DE4SDV INC-AEBS-010 read-only AEBS visualization source bridge.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bridge = de4sdv_aebs_010_bridge.ros_node:main",
        ],
    },
)
