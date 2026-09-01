// DE4SDV INC-AEBS-010 native ingress service.
//
// Connects read-only to the ROS-side frame server, validates each bounded
// protobuf frame, and republishes accepted frames through the SDV Gateway
// Data Tunnel. No command path is exposed.

#include "validator.h"

#include <android-base/properties.h>
#include <android/binder_process.h>
#include <android/log.h>
#include <libsdvgatewayclient.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace {
constexpr char kFrameServerHostProperty[] = "de4sdv.aebs.frame_server.host";
constexpr char kFrameServerPortProperty[] = "de4sdv.aebs.frame_server.port";
// Bench bound: vmB and the Cuttlefish guest clocks are unsynchronized, so the
// sink-side future-skew check uses a 10-minute bound for this bench segment.
// Production deployment requires synchronized clocks and the 100 ms bound
// (AO-AEBS-010-005); this relaxation is a documented bench-only disposition.
constexpr int64_t kMaxFutureSkewNs = 600'000'000'000;
constexpr int64_t kStaleTimeoutNs = 1'000'000'000;
constexpr size_t kMaxFrameBytes = 1'048'576;
constexpr size_t kGatewaySlotBytes = 2048;
constexpr char kTopic[] = "aebs-visualization-frame";

void LogInfo(const std::string& message) {
  __android_log_print(ANDROID_LOG_INFO, "de4sdv_aebs_ingress", "%s", message.c_str());
}
void LogWarning(const std::string& message) {
  __android_log_print(ANDROID_LOG_WARN, "de4sdv_aebs_ingress", "%s", message.c_str());
}
void LogError(const std::string& message) {
  __android_log_print(ANDROID_LOG_ERROR, "de4sdv_aebs_ingress", "%s", message.c_str());
}

const char* GatewayError(const ASDVGateway_Status_t& status) {
  return status.errorMessage == nullptr ? "(no message)" : status.errorMessage;
}

void Fill(const char* value, char* destination, size_t capacity) {
  std::strncpy(destination, value, capacity - 1);
  destination[capacity - 1] = '\0';
}

bool CreateGatewayPublication(ASDVGateway_Client** client_out, int32_t* publication_id_out) {
  ABinderProcess_setThreadPoolMaxThreadCount(1);
  ABinderProcess_startThreadPool();

  ASDVGateway_Status_t status{};
  ASDVGateway_Client* client = nullptr;
  if (ASDVGateway_Client_new(&client, &status) != ASDVGateway_StatusCode_OK) {
    LogError("Gateway client_new failed: " + std::to_string(status.statusCode) + " " +
             GatewayError(status));
    return false;
  }

  ASDVGateway_InitCommsParams_t init{};
  Fill("de4sdv.aebs_visualization", init.packageName, sizeof(init.packageName));
  Fill("AebsVisualization", init.serviceBundleName, sizeof(init.serviceBundleName));
  Fill("default", init.serviceInstanceName, sizeof(init.serviceInstanceName));
  if (ASDVGateway_Client_initComms(client, &init, &status) != ASDVGateway_StatusCode_OK) {
    LogError("Gateway initComms failed: " + std::to_string(status.statusCode) + " " +
             GatewayError(status));
    return false;
  }

  ASDVGateway_CreatePublicationParams_t params{};
  Fill(kTopic, params.serviceUnitName, sizeof(params.serviceUnitName));
  Fill("de4sdv.aebs_visualization.v1", params.unitType.sdvPackageName,
       sizeof(params.unitType.sdvPackageName));
  Fill("AebsVisualization", params.unitType.serviceBundleName,
       sizeof(params.unitType.serviceBundleName));
  Fill("VisualizationFrame", params.unitType.unitTypeName,
       sizeof(params.unitType.unitTypeName));
  params.publisherUnitMetadata.version = 1;
  params.publisherUnitMetadata.messageSizeBytes = kGatewaySlotBytes;
  params.publisherUnitMetadata.messageCount = 16;

  ASDVGateway_PublicationMetadata_t metadata{};
  if (ASDVGateway_Client_createPublication(client, &params, &metadata, &status) !=
      ASDVGateway_StatusCode_OK) {
    LogError("Gateway createPublication failed: " + std::to_string(status.statusCode) + " " +
             GatewayError(status));
    return false;
  }
  *client_out = client;
  *publication_id_out = metadata.publicationId;
  LogInfo("Gateway publication active id=" + std::to_string(metadata.publicationId));
  return true;
}

std::vector<uint8_t> BuildGatewaySlot(
    const de4sdv::aebs_visualization::v1::VisualizationFrame& frame) {
  std::string message;
  if (!frame.SerializeToString(&message)) return {};

  std::vector<uint8_t> slot(kGatewaySlotBytes, 0);
  uint32_t size = static_cast<uint32_t>(message.size());
  size_t offset = 0;
  do {
    if (offset >= slot.size()) return {};
    uint8_t byte = static_cast<uint8_t>(size & 0x7fU);
    size >>= 7U;
    if (size != 0U) byte |= 0x80U;
    slot[offset++] = byte;
  } while (size != 0U);
  if (offset + message.size() > slot.size()) return {};
  std::memcpy(slot.data() + offset, message.data(), message.size());
  return slot;
}

bool PublishFrame(ASDVGateway_Client* client, int32_t publication_id,
                  const de4sdv::aebs_visualization::v1::VisualizationFrame& frame) {
  const std::vector<uint8_t> slot = BuildGatewaySlot(frame);
  if (slot.empty()) {
    LogError("Gateway slot serialization failed");
    return false;
  }
  ASDVGateway_Status_t status{};
  if (ASDVGateway_Client_publishMessages(client, slot.data(), slot.size(), publication_id,
                                         &status) != ASDVGateway_StatusCode_OK) {
    LogError("Gateway publishMessages failed: " + std::to_string(status.statusCode) + " " +
             GatewayError(status));
    return false;
  }
  return true;
}

int ConnectToFrameServer() {
  const std::string host =
      android::base::GetProperty(kFrameServerHostProperty, "10.250.0.3");
  const int port =
      android::base::GetIntProperty(kFrameServerPortProperty, 4721);

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(static_cast<uint16_t>(port));
  if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
    LogError("invalid frame server host: " + host);
    return -1;
  }
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    LogError(std::string("socket: ") + strerror(errno));
    return -1;
  }
  if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
    LogError("connect to frame server " + host + ":" + std::to_string(port) + ": " +
             strerror(errno));
    close(fd);
    return -1;
  }
  LogInfo("connected to frame server " + host + ":" + std::to_string(port));
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
  // Establish the read-only bench transport before gateway registration.
  // The gateway runtime applies service-network policy to the registered
  // process; an already-connected socket retains the explicitly bounded
  // vmA-host proxy route used by the Cuttlefish guest.
  const int frame_fd = ConnectToFrameServer();
  if (frame_fd < 0) return 1;

  ASDVGateway_Client* gateway_client = nullptr;
  int32_t publication_id = 0;
  if (!CreateGatewayPublication(&gateway_client, &publication_id)) return 1;

  uint64_t last_accepted_sequence = 0;
  uint8_t length_prefix[4];
  std::string payload;

  while (true) {
    if (!ReadFull(frame_fd, length_prefix, sizeof(length_prefix))) {
      LogError("frame server closed the stream");
      break;
    }
    const uint32_t frame_length =
        static_cast<uint32_t>(length_prefix[0]) |
        (static_cast<uint32_t>(length_prefix[1]) << 8) |
        (static_cast<uint32_t>(length_prefix[2]) << 16) |
        (static_cast<uint32_t>(length_prefix[3]) << 24);
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

    timespec timestamp{};
    clock_gettime(CLOCK_REALTIME, &timestamp);
    const int64_t now_ns =
        static_cast<int64_t>(timestamp.tv_sec) * 1'000'000'000 + timestamp.tv_nsec;
    const de4sdv_aebs010::ValidationResult verdict = de4sdv_aebs010::validate_frame(
        frame, last_accepted_sequence, now_ns, kMaxFutureSkewNs, kStaleTimeoutNs);
    if (!verdict.accepted) {
      LogWarning("frame rejected: " + verdict.reason);
      continue;
    }
    if (!PublishFrame(gateway_client, publication_id, frame)) break;
    last_accepted_sequence = frame.sequence();
    LogInfo("frame accepted and published sequence=" + std::to_string(frame.sequence()));
  }

  close(frame_fd);
  return 1;
}
