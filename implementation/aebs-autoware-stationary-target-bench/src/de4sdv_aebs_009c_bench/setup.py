from setuptools import find_packages, setup

PACKAGE = "de4sdv_aebs_009c_bench"

setup(
    name="de4sdv_aebs_009c_bench",
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/launch", ["launch/aebs_009c_bench.launch.py"]),
        (
            f"share/{PACKAGE}/config",
            ["../../config/scenario-009c-aeb-mrm.yaml"],
        ),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="DE4SDV maintainers",
    maintainer_email="maintainers@de4sdv.org",
    description="Partial INC-AEBS-009C native-AEB-intervention to MRM/gate evidence fixture.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "scenario_fixture = de4sdv_aebs_009c_bench.scenario_fixture:main",
            "scenario_observer = de4sdv_aebs_009c_bench.scenario_observer:main",
        ]
    },
)
