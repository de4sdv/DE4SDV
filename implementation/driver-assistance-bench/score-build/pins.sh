# DE4SDV driver-assistance bench (INC-DRIVING-002): every pinned input of the S-CORE build and of the GPU runtime.
# Sourced by build_score_bench.sh, install_gpu_runtime.sh and fallback_cmake_build.sh; read by tests/.
# Each direct download has a URL and the sha256 of the file downloaded on 2026-11-18 (computed with sha256sum; for
# the NVIDIA archives also equal to NVIDIA's redistrib manifest). Each git source is pinned by its full commit id.
# shellcheck disable=SC2034

# --- Git sources (commit ids) -------------------------------------------------------------------------------------
VP_URL=https://github.com/autowarefoundation/vision_pilot.git
VP_COMMIT=014e0e7a56ee8e597c2cab8175233f74edd9b856
FEO_URL=https://github.com/eclipse-score/feo.git
FEO_COMMIT=313b3d849c17881d3a11b6bf62aa2afab6565ef0
GATEWAY_URL=https://github.com/eclipse-score/inc_someip_gateway.git
GATEWAY_COMMIT=d9eac670b7534352749da3d30f52aebf5129f168
CARLA_URL=https://github.com/carla-simulator/carla.git
CARLA_COMMIT=14ac3b1a502da45a44506cb2ed82ab800f1baf4c

# --- Build tools --------------------------------------------------------------------------------------------------
# Bazel binaries, called directly (no bazelisk). FEO's .bazelversion; its .bazeliskrc selects the Aspect CLI 5.9.36
# wrapper of this Bazel, which DA-P8 e used; plain Bazel is used here so that the binary can be pinned by sha256.
BAZEL_FEO_VERSION=8.3.0
BAZEL_FEO_SHA256=55ba395ed114ee35ee9add63fbc44fa46a6b518b3c2f6d0211a574957cddde2d
# the gateway's .bazelversion; the same sha256 as the score-reference-interop-bench workflow
BAZEL_GATEWAY_VERSION=8.6.0
BAZEL_GATEWAY_SHA256=9860da9c9386bbc023feed8f43af3105d338727d77b644fa6aeca45a4a11957c
# CARLA 14ac3b1a50 needs CMake >= 3.27.2; Ubuntu 22.04 ships 3.22
CMAKE_URL=https://github.com/Kitware/CMake/releases/download/v3.28.3/cmake-3.28.3-linux-x86_64.tar.gz
CMAKE_SHA256=804d231460ab3c8b556a42d2660af4ac7a0e21c98a7f8ee3318a74b4a9a187a6

# --- Third-party sources and prebuilt libraries --------------------------------------------------------------------
OPENCV_URL=https://github.com/opencv/opencv/archive/refs/tags/4.6.0.tar.gz
OPENCV_SHA256=1ec1cba65f9f20fe5a41fda1586e01c70ea0c9a6d7b67c9e13edf0cfe2239277
# the version VisionPilot's logging/CMakeLists.txt fetches
RERUN_URL=https://github.com/rerun-io/rerun/releases/download/0.34.1/rerun_cpp_sdk.zip
RERUN_SHA256=b92ece5bbaedbdfb0405f50a357440442d7abbede44af33e429cf3b7ea4749c2
# the tag VisionPilot's planning/CMakeLists.txt fetches
EIGEN_URL=https://gitlab.com/libeigen/eigen/-/archive/5.0.0/eigen-5.0.0.tar.gz
EIGEN_SHA256=315c881e19e17542a7d428c5aa37d113c89b9500d350c433797b730cd449c056
# ONNX Runtime 1.26.0 (the version of VisionPilot's docker/Dockerfile), Microsoft's prebuilt GPU package for Linux
# on nuget.org (release branch rel-1.26.0, commit 8c546c37b43caaca1fa25db430dab94b901cf277). The GitHub release
# assets were unreachable on 2026-11-18 (github.com/microsoft/onnxruntime answered 404). ORT's CUDA provider
# requirements table: 1.26.x is built with CUDA 12.8 and cuDNN 9.x; the CUDA 13.0 default starts with 1.27.
# readelf of libonnxruntime_providers_cuda.so agrees: it needs the CUDA 12 sonames below.
ORT_VERSION=1.26.0
ORT_URL=https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime.gpu.linux/1.26.0/microsoft.ml.onnxruntime.gpu.linux.1.26.0.nupkg
ORT_SHA256=cf7943f58b9360fe1448c4baf40ac12ce4175978ecd3fe6f21a4c00976f63a59
ORT_LIBONNXRUNTIME_SHA256=ea322d74879c376217a310e4233e4f50ea9267a0e339963d0e1961f46b7a57d5
ORT_PROVIDERS_CUDA_SHA256=ab84f752c77a70f3201bea09548dc70f82c5dc6e0c532197af659ae8b5225f90
ORT_PROVIDERS_SHARED_SHA256=c6a12593396095f5670160e284c35d1700b7708cf3037b7042e2a5200ccae772
ORT_CUDA_NEEDED="libcublasLt.so.12 libcublas.so.12 libcurand.so.10 libcufft.so.11 libcudart.so.12 libcudnn.so.9"

# The SOME/IP gateway's sample type, which the S-CORE interface module's mw::com binding uses
GATEWAY_PRE_SERIALIZED_DATA_SHA256=1ec7b4c961044559195e50a2c364b47792c444ea6e497fe6c2a9aac7d6a1b2f8

# --- Ubuntu 22.04 packages (apt verifies them against the signed archive; versions as of 2026-11-18) ----------------
# Planning's solver: Ipopt and CppAD, as upstream's docker/Dockerfile installs them (coinor-libipopt-dev, libcppad-dev)
APT_PINNED="coinor-libipopt-dev=3.11.9-2.2build5 libcppad-dev=2021.00.00.8-1"
# Build tools, the GStreamer development files for OpenCV's videoio, and python3-opencv with python3-numpy for upstream's
# find_homography_C_matrix.py (versions recorded in the bundle)
APT_BUILD="build-essential g++ git curl unzip xz-utils file binutils ninja-build pkg-config python3 python3-opencv
 python3-numpy libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev nlohmann-json3-dev"
# What the S-CORE host needs at run time beside the bundle (installed by install_gpu_runtime.sh)
APT_RUNTIME="libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 libgstreamer-plugins-bad1.0-0 gstreamer1.0-plugins-base
 gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-tools"

# --- GPU runtime for the S-CORE host (NVIDIA L4, driver 580): CUDA 12.8 Update 1 and cuDNN 9.28.1.4 for CUDA 12 ------
# From NVIDIA's redistributable archives; sha256 as in redistrib_12.8.1.json and cudnn redistrib_9.28.1.json
CUDA_VERSION=12.8.1
CUDA_REDIST=https://developer.download.nvidia.com/compute/cuda/redist
CUDA_MANIFEST_SHA256=249e28a83008d711d5f72880541c8be6253f6d61608461de4fcb715554a6cf17
CUDNN_VERSION=9.28.1.4
CUDNN_REDIST=https://developer.download.nvidia.com/compute/cudnn/redist
CUDNN_MANIFEST_SHA256=0c579b4897afeeba4e7349beb39f7f91eefd50fb566db79201b5729974d48cc1
# name|relative path|sha256|size in bytes
CUDA_ARCHIVES="
cuda_cudart|cuda_cudart/linux-x86_64/cuda_cudart-linux-x86_64-12.8.90-archive.tar.xz|8d566b5fe745c46842dc16945cf36686227536decd2302c372be86da37faca68|1354240
libcublas|libcublas/linux-x86_64/libcublas-linux-x86_64-12.8.4.1-archive.tar.xz|21718957c2cf000bacd69d36c95708a2319199e39e056f8b4f0f68e3b9f323bb|938651324
libcufft|libcufft/linux-x86_64/libcufft-linux-x86_64-11.3.3.83-archive.tar.xz|126fe08fc0df07a7420c2da05a2ae72ea19660fff79bf06de16520d1f915cb83|448695100
libcurand|libcurand/linux-x86_64/libcurand-linux-x86_64-10.3.9.90-archive.tar.xz|32a5ec30be446c1b7228d1bc502b2f029cc8b59a5e362c70d960754fa646778b|88606668
cuda_nvrtc|cuda_nvrtc/linux-x86_64/cuda_nvrtc-linux-x86_64-12.8.93-archive.tar.xz|992f5e4d95cb499f41e442245efa877dbd60c711451afe680a26700d61eb3843|114287212
libnvjitlink|libnvjitlink/linux-x86_64/libnvjitlink-linux-x86_64-12.8.93-archive.tar.xz|29220664ad272c513d3213133ace6d6590303e46b42a17b05bc2bee90e54a888|53997360
"
CUDNN_ARCHIVES="
cudnn|cudnn/linux-x86_64/cudnn-linux-x86_64-9.28.1.4_cuda12-archive.tar.xz|bcd9fdf9e80812e400954eb948b1b59f41ac8bd20fd990d9aa5ada32745e6253|1027537968
"
# The lowest driver branch the scripts accept for CUDA 12.8 without the compatibility package
CUDA_MIN_DRIVER_MAJOR=570
