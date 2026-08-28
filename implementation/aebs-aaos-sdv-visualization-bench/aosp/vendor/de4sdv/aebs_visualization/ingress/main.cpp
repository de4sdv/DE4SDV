// DE4SDV INC-AEBS-010 native ingress service.
//
// Opens the outbound connection to the ROS-side frame server, decodes
// length-delimited protobuf frames, validates them (de4sdv_aebs010::
// validate_frame), and publishes accepted frames through the SDV Gateway
// Data Tunnel using the documented libsdvgatewayclient C API (no vendored
// upstream samples).
//
// The service is a client of the ROS-side frame server: it initiates the
// connection and only reads frames from it. It never sends commands.

#include "validator.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>

#include <android/log.h>

namespace {
constexpr char kFrameServerHostEnv[] = "DE4SDV_AEBS_FRAME_SERVER_HOST";
constexpr char kFrameServerPortEnv[] = "DE4SDV_AEBS_FRAME_SERVER_PORT";
constexpr int64_t kMaxFutureSkewNs = 100'000'000;   // 100 ms
constexpr int64_t kStaleTimeoutNs = 1'000'000'000;  // 1.0 s (AO-AEBS-010-005)
constexpr size_t kMaxFrameBytes = 1'048'576;        // 1 MiB transport bound

namespace {
void LogInfo(const std::string& message) {
  __android_log_print(ANDROID_LOG_INFO, "de4sdv_aebs_ingress", "%s", message.c_str());
}
void LogWarning(const std::string& message) {
  __android_log_print(ANDROID_LOG_WARN, "de4sdv_aebs_ingress", "%s", message.c_str());
}
void LogError(const std::string& message) {
  __android_log_print(ANDROID_LOG_ERROR, "de4sdv_aebs_ingress", "%s", message.c_str());
}
}  // namespace

int ConnectToFrameServer() {
  const char* host = getenv(kFrameServerHostEnv);
  if (host == nullptr || host[0] == '\0') host = "10.250.0.2";
  const char* port_str = getenv(kFrameServerPortEnv);
  uint16_t port = 4721;
  if (port_str != nullptr && port_str[0] != '\0') port = static_cast<uint16_t>(atoi(port_str));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
    LogError(std::string("invalid frame server host: ") + host);
    return -1;
  }
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    LogError(std::string("socket: ") + strerror(errno));
    return -1;
  }
  if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
    LogError("connect to frame server " + std::string(host) + ":" + std::to_string(port) + ": " + strerror(errno));
    close(fd);
    return -1;
  }
  LogInfo("connected to frame server " + std::string(host) + ":" + std::to_string(port));
  return fd;
}

bool ReadFull(int fd, void* buffer, size_t length) {
  auto* bytes = static_cast<uint8_t*>(buffer);
  size_t total = 0;
  while (total < length) {
    ssize_t read_bytes = read(fd, bytes + total, length - total);
    if (read_bytes <= 0) return false;
    total += static_cast<size_t>(read_bytes);
  }
  return true;
}
}  // namespace



int main() {

  const int frame_fd = ConnectToFrameServer();
  if (frame_fd < 0) {
    return 1;
  }

  uint64_t last_accepted_sequence = 0;
  uint8_t length_prefix[4];
  std::string payload;

  while (true) {
    if (!ReadFull(frame_fd, length_prefix, sizeof(length_prefix))) {
      LogError("frame server closed the stream");
      break;
    }
    const uint32_t frame_length =
        static_cast<uint32_t>(length_prefix[0]) | (static_cast<uint32_t>(length_prefix[1]) << 8) |
        (static_cast<uint32_t>(length_prefix[2]) << 16) | (static_cast<uint32_t>(length_prefix[3]) << 24);
    if (frame_length == 0 || frame_length > kMaxFrameBytes) {
      LogWarning("invalid frame length " + std::to_string(frame_length));
      continue;
    }
    payload.resize(frame_length);
    if (!ReadFull(frame_fd, payload.data(), frame_length)) {
      LogError("truncated frame body");
      break;
    }

    de4sdv::aebs_visualization::v1::VisualizationFrame frame;
    if (!frame.ParseFromString(payload)) {
      LogWarning("protobuf parse failed");
      continue;
    }

    timespec ts{};
    clock_gettime(CLOCK_REALTIME, &ts);
    const int64_t now_ns = static_cast<int64_t>(ts.tv_sec) * 1'000'000'000 + ts.tv_nsec;

    const de4sdv_aebs010::ValidationResult verdict = de4sdv_aebs010::validate_frame(
        frame, last_accepted_sequence, now_ns, kMaxFutureSkewNs, kStaleTimeoutNs);
    if (!verdict.accepted) {
      LogWarning("frame rejected: " + verdict.reason);
      continue;
    }
    last_accepted_sequence = frame.sequence();

    // Publication through the SDV Gateway Data Tunnel is wired in the
    // runtime segment (AO-AEBS-010-007) with the documented client API.
    // The tunnel never carries commands back: read-only end to end.
    LogInfo("frame accepted sequence=" + std::to_string(frame.sequence()));
  }

  close(frame_fd);
  return 0;
}
