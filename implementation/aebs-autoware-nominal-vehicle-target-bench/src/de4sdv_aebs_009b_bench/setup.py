from setuptools import find_packages, setup

PACKAGE = "de4sdv_aebs_009b_bench"

setup(
    name="de4sdv_aebs_009b_bench",
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/launch", ["launch/aebs_009b_bench.launch.py"]),
        (
            f"share/{PACKAGE}/config",
            [
                "../../config/scenario-009b-moving-vehicle-target.yaml",
                "../../config/scenario-009d-conscious-override-matrix.yaml",
                "../../config/scenario-009d-moving-vehicle-target.yaml",
                "../../config/aebs-009b.param.yaml",
            ],
        ),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="DE4SDV maintainers",
    maintainer_email="maintainers@de4sdv.org",
    description="Nominal INC-AEBS-009B moving-vehicle-target integration evidence fixture.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "scenario_fixture = de4sdv_aebs_009b_bench.scenario_fixture:main",
            "aebs_coordinator = de4sdv_aebs_009b_bench.aebs_coordinator:main",
            "scenario_observer = de4sdv_aebs_009b_bench.scenario_observer:main",
        ]
    },
)
