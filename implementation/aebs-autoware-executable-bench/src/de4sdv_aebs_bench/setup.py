from setuptools import find_packages, setup

PACKAGE = "de4sdv_aebs_bench"

setup(
    name=PACKAGE,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/launch", ["launch/aebs_bench.launch.py"]),
        (
            f"share/{PACKAGE}/config",
            [
                "config/aebs.param.yaml",
                "config/diagnostic-graph.yaml",
                "config/pointcloud_map_loader.param.yaml",
                "config/lanelet2_map_loader.param.yaml",
                "config/map_tf_generator.param.yaml",
                "config/map_projection_loader.param.yaml",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="DE4SDV maintainers",
    maintainer_email="maintainers@de4sdv.org",
    description="INC-AEBS-009A executable launch and readiness bench.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "readiness_collector = de4sdv_aebs_bench.readiness_collector:main",
            "nominal_fixture = de4sdv_aebs_bench.nominal_fixture:main",
        ]
    },
)
