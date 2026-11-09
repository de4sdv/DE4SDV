# The uv-managed CPython 3.12.16 (python-build-standalone) for drivingAgent's embedded planner,
# imported into the FEO workspace by new_local_repository(name = "python312", ...): see
# agent/workspace/README.md.
#   :python              the versioned library (rules_cc links it by path; the WP2a probe)
#   :python_unversioned  the same library through its unversioned name, for rust_binary links:
#                        rules_rust passes -lpython3.12, which resolves only to libpython3.12.so.
# At run time the loader finds libpython3.12.so.1.0 (the SONAME) through LD_LIBRARY_PATH.
cc_library(
    name = "python",
    srcs = ["lib/libpython3.12.so.1.0"],
    hdrs = glob(["include/python3.12/**/*.h"]),
    includes = ["include/python3.12"],
    visibility = ["//visibility:public"],
)

cc_library(
    name = "python_unversioned",
    srcs = ["lib/libpython3.12.so"],
    hdrs = glob(["include/python3.12/**/*.h"]),
    includes = ["include/python3.12"],
    visibility = ["//visibility:public"],
)
