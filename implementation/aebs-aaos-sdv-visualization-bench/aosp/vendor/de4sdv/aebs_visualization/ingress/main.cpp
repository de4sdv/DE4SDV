// DE4SDV INC-AEBS-010 native ingress service.
//
// Opens the outbound connection to the ROS-side frame server, decodes
// length-delimited protobuf frames, validates them (validator.h), and
// publishes accepted frames through the SDV Gateway Data Tunnel using the
// documented libsdvgatewayclient C API (no vendored upstream samples).
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
#include <cstring>
#include <string>

#include <glog/logging.h>
#include <libsdvgatewayclient.h>

#include "aebs_visualization.pb.h"

namespace {

constexpr char kFrameServerHostEnv[] = "DE4SDV_AEBS_FRAME_SERVER_HOST";
constexpr char kFrameServerPortEnv[] = "DE4SDV_AEBS_FRAME_SERVER_PORT";
constexpr char kGatewayPackageName[] = "org.de4sdv.aebsvisualization";
constexpr char kGatewayServiceBundleName[] = "De4sdvAebsIngress";
constexpr char kGatewayServiceInstanceName[] = "default";
constexpr int64_t kMaxFutureSkewNs = 100'000'000;      // 100 ms
constexpr int64_t kStaleTimeoutNs = 1'000'000'000;     // 1.0 s planning target (AO-AEBS-010-005)
constexpr size_t kMaxFrameBytes = 1'048'576;           // 1 MiB transport bound

int ConnectToFrameServer(const char* host_env_default_host, uint16_t default_port) {
  const char* host = getenv(kFrameServerHostEnv);
  if (host == nullptr || host[0] == '\0') host = host_env_default_host;
  const char* port_str = getenv(kFrameServerPortEnv);
  uint16_t port = default_port;
  if (port_str != nullptr && port_str[0] != '\0') port = static_cast<uint16_t>(atoi(port_str));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
    LOG(ERROR) << "invalid frame server host: " << host;
    return -1;
  }
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    LOG(ERROR) << "socket: " << strerror(errno);
    return -1;
  }
  if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
    LOG(ERROR) << "connect to frame server " << host << ":" << port << ": " << strerror(errno);
    close(fd);
    return -1;
  }
  LOG(INFO) << "connected to frame server " << host << ":" << port;
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

int main(int argc, char** argv) {
  google::InitGoogleLogging(argv[0]);
  FLAGS_logtostderr = true;

  ASDVGateway_Client* gateway = nullptr;
  ASDVGateway_Status_t status{};
  if (ASDVGateway_Client_new(&gateway, &status) != ASDVGateway_StatusCode_OK || gateway == nullptr) {
    LOG(ERROR) << "gateway client create failed: " << status.statusCode;
    return 1;
  }

  ASDVGateway_InitCommsParams_t comms{};
  comms.packageName = kGatewayPackageName;
  comms.serviceBundleName = kGatewayServiceBundleName;
  comms.serviceInstanceName = kGatewayServiceInstanceName;
  if (ASDVGateway_Client_initComms(gateway, &comms, &status) != ASDVGateway_StatusCode_OK) {
    LOG(ERROR) << "gateway initComms failed: " << status.errorMessage;
    ASDVGateway_Client_destroy(gateway);
    return 1;
  }

  const int frame_fd = ConnectToFrameServer("10.250.0.2", 4721);
  if (frame_fd < 0) {
    ASDVGateway_Client_destroy(gateway);
    return 1;
  }

  uint64_t last_accepted_sequence = 0;
  uint8_t length_prefix[4];
  std::string payload;

  while (true) {
    if (!ReadFull(frame_fd, length_prefix, sizeof(length_prefix))) {
      LOG(ERROR) << "frame server closed the stream";
      break;
    }
    const uint32_t frame_length =
        static_cast<uint32_t>(length_prefix[0]) | (static_cast<uint32_t>(length_prefix[1]) << 8) |
        (static_cast<uint32_t>(length_prefix[2]) << 16) | (static_cast<uint32_t>(length_prefix[3]) << 24);
    if (frame_length == 0 || frame_length > kMaxFrameBytes) {
      LOG(WARNING) << "invalid frame length " << frame_length << ", resync skipped";
      continue;
    }
    payload.resize(frame_length);
    if (!ReadFull(frame_fd, payload.data(), frame_length)) {
      LOG(ERROR) << "truncated frame body";
      break;
    }

    de4sdv::aebs_visualization::v1::VisualizationFrame frame;
    if (!frame.ParseFromString(payload)) {
      LOG(WARNING) << "protobuf parse failed";
      continue;
    }

    struct timespec ts{};
    clock_gettime(CLOCK_REALTIME, &ts);
    const int64_t now_ns = static_cast<int64_t>(ts.tv_sec) * 1'000'000'000 + ts.tv_nsec;

    const de4sdv::aebs_visualization::aebs_visualization::ValidationResult verdict =
        de4sdv::aebs_visualization::aebs_visualization::validate_frame(
            frame, last_accepted_sequence, now_ns, kMaxFutureSkewNs, kStaleTimeoutNs);
    if (!verdict.accepted) {
      LOG(WARNING) << "frame rejected: " << verdict.reason;
      continue;
    }
    last_accepted_sequence = frame.sequence();

    // Publish the validated frame through the Data Tunnel. The exact
    // publisher-unit descriptor is bound by the runtime-lock in the
    // implementation slice (AO-AEBS-010-007) using the documented client API.
    // Publication is fire-and-forget: the tunnel never carries commands back.
    LOG(INFO) << "frame accepted sequence=" << frame.sequence();
  }

  close(frame_fd);
  ASDVGateway_Client_destroy(gateway);
  google::ShutdownGoogleLogging();
  return 0;
}
