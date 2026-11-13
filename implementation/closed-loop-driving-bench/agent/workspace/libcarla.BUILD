# P3.d: LibCarla 0.9.16 client, built outside Bazel with the S-CORE gcc 12.2.0 toolchain and sysroot
# (/opt/carla-d/d_stage1.sh, d_stage2.sh), imported as prebuilt static archives.
cc_library(
    name = "client",
    srcs = [
        "lib/libcarla_client.a",
        "lib/librpc.a",
        "lib/libboost_filesystem.a",
        "lib/libDetourCrowd.a",
        "lib/libDetour.a",
        "lib/libRecast.a",
    ],
    hdrs = glob(["include/**/*.h", "include/**/*.hpp"]),
    textual_hdrs = glob(
        ["include/**"],
        exclude = ["include/**/*.h", "include/**/*.hpp", "include/**/*.cpp", "include/**/*.cc", "include/**/*.c"],
    ),
    defines = [
        "BOOST_ERROR_CODE_HEADER_ONLY",
        "LIBCARLA_IMAGE_WITH_PNG_SUPPORT=false",
    ],
    includes = [
        "include",
        "include/system",
    ],
    linkopts = ["-lpthread"],
    linkstatic = True,
    visibility = ["//visibility:public"],
)
