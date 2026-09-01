// DE4SDV INC-AEBS-010 PF-004 probe: native SDV Gateway publisher.
// Bench-only state exerciser. It publishes fixed-size Data Tunnel slots carrying
// one varint-delimited VisualizationFrame. Invalid mode deliberately replays a
// lower sequence so the display exercises its fail-closed envelope guard.
// No product claim.

#include <libsdvgatewayclient.h>
#include <android/binder_process.h>

#include "aebs_visualization.pb.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unistd.h>
#include <vector>

namespace {
constexpr size_t kGatewaySlotBytes = 2048;

enum class Mode { kHealthy, kWarning, kIntervention, kRelease, kInvalid };

void Fill(const char* value, char* dest, size_t size) {
  std::strncpy(dest, value, size - 1);
  dest[size - 1] = '\0';
}

const char* Err(const ASDVGateway_Status_t& status) {
  return status.errorMessage != nullptr ? status.errorMessage : "(no message)";
}

const char* ModeName(Mode mode) {
  switch (mode) {
    case Mode::kHealthy: return "healthy";
    case Mode::kWarning: return "warning";
    case Mode::kIntervention: return "intervention";
    case Mode::kRelease: return "release";
    case Mode::kInvalid: return "invalid";
  }
  return "unknown";
}

bool ParseMode(const char* text, Mode* mode) {
  if (std::strcmp(text, "healthy") == 0) *mode = Mode::kHealthy;
  else if (std::strcmp(text, "warning") == 0) *mode = Mode::kWarning;
  else if (std::strcmp(text, "intervention") == 0) *mode = Mode::kIntervention;
  else if (std::strcmp(text, "release") == 0) *mode = Mode::kRelease;
  else if (std::strcmp(text, "invalid") == 0) *mode = Mode::kInvalid;
  else return false;
  return true;
}

de4sdv::aebs_visualization::v1::VisualizationFrame BuildFrame(
    uint64_t sequence, Mode mode) {
  de4sdv::aebs_visualization::v1::VisualizationFrame frame;
  const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                             std::chrono::system_clock::now().time_since_epoch())
                             .count();
  frame.set_schema_major(1);
  frame.set_schema_minor(0);
  frame.set_sequence(sequence);
  frame.set_frame_timestamp_ns(now_ns);
  frame.set_bridge_receipt_timestamp_ns(now_ns);
  frame.set_source_identity(std::string("INC-AEBS-010-PF004-") + ModeName(mode));

  auto* intervention = frame.mutable_native_intervention();
  intervention->set_source_kind(
      de4sdv::aebs_visualization::v1::SOURCE_KIND_NATIVE_AUTOWARE_AEB);
  intervention->set_source_timestamp_ns(now_ns);
  intervention->set_units("boolean");
  intervention->set_coordinate_frame("none");
  intervention->set_bool_value(mode == Mode::kIntervention);

  auto* warning = frame.mutable_de4sdv_warning_request();
  warning->set_source_kind(
      de4sdv::aebs_visualization::v1::SOURCE_KIND_DE4SDV_AEBS_COORDINATOR);
  warning->set_source_timestamp_ns(now_ns);
  warning->set_units("boolean");
  warning->set_coordinate_frame("none");
  warning->set_bool_value(mode == Mode::kWarning || mode == Mode::kIntervention);

  auto* braking = frame.mutable_de4sdv_braking_request();
  braking->CopyFrom(*warning);
  braking->set_bool_value(mode == Mode::kIntervention);

  auto* lifecycle = frame.mutable_de4sdv_lifecycle_state();
  lifecycle->set_source_kind(
      de4sdv::aebs_visualization::v1::SOURCE_KIND_DE4SDV_AEBS_COORDINATOR);
  lifecycle->set_source_timestamp_ns(now_ns);
  lifecycle->set_units("enum");
  lifecycle->set_coordinate_frame("none");
  lifecycle->set_enum_value(mode == Mode::kRelease ? "released_verified_stop" :
                            mode == Mode::kIntervention ? "braking_latched" : "armed");
  return frame;
}

std::vector<uint8_t> BuildSlot(uint64_t sequence, Mode mode) {
  std::vector<uint8_t> slot(kGatewaySlotBytes, 0);
  std::string message;
  if (!BuildFrame(sequence, mode).SerializeToString(&message)) return {};
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
}  // namespace

int main(int argc, char** argv) {
  bool loop = false;
  Mode mode = Mode::kHealthy;
  uint64_t sequence_base = 1'000'000;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "-l") == 0) {
      loop = true;
    } else if (std::strcmp(argv[i], "--mode") == 0 && i + 1 < argc &&
               ParseMode(argv[i + 1], &mode)) {
      ++i;
    } else if (std::strcmp(argv[i], "--sequence-base") == 0 && i + 1 < argc) {
      sequence_base = std::strtoull(argv[++i], nullptr, 10);
    } else {
      std::fprintf(stderr,
                   "usage: %s [-l] [--mode healthy|warning|intervention|release|invalid] "
                   "[--sequence-base uint64]\n",
                   argv[0]);
      return 2;
    }
  }

  ABinderProcess_setThreadPoolMaxThreadCount(1);
  ABinderProcess_startThreadPool();

  ASDVGateway_Client* client = nullptr;
  ASDVGateway_Status_t status{};
  if (ASDVGateway_Client_new(&client, &status) != ASDVGateway_StatusCode_OK) {
    std::printf("PF004 client_new failed: %d %s\n",
                static_cast<int>(status.statusCode), Err(status));
    return 1;
  }
  std::printf("PF004 client_new ok\n");

  ASDVGateway_InitCommsParams_t init{};
  Fill("de4sdv.aebs_visualization", init.packageName, sizeof(init.packageName));
  Fill("AebsVisualization", init.serviceBundleName, sizeof(init.serviceBundleName));
  Fill("default", init.serviceInstanceName, sizeof(init.serviceInstanceName));
  if (ASDVGateway_Client_initComms(client, &init, &status) !=
      ASDVGateway_StatusCode_OK) {
    std::printf("PF004 initComms failed: %d %s\n",
                static_cast<int>(status.statusCode), Err(status));
    return 1;
  }
  std::printf("PF004 initComms ok\n");

  ASDVGateway_CreatePublicationParams_t params{};
  Fill("aebs-visualization-frame", params.serviceUnitName, sizeof(params.serviceUnitName));
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
    std::printf("PF004 createPublication failed: %d %s\n",
                static_cast<int>(status.statusCode), Err(status));
    return 1;
  }
  std::printf("PF004 createPublication ok id=%d mode=%s\n",
              metadata.publicationId, ModeName(mode));

  uint64_t sequence = sequence_base;
  auto publish_frame = [&]() -> bool {
    const std::vector<uint8_t> payload = BuildSlot(sequence++, mode);
    if (payload.size() != kGatewaySlotBytes) {
      std::fprintf(stderr, "PF004 frame serialization failed\n");
      return false;
    }
    if (ASDVGateway_Client_publishMessages(client, payload.data(), payload.size(),
                                           metadata.publicationId, &status) !=
        ASDVGateway_StatusCode_OK) {
      std::printf("PF004 publishMessages failed: %d %s\n",
                  static_cast<int>(status.statusCode), Err(status));
      return false;
    }
    return true;
  };

  for (int i = 0; i < 5; ++i) {
    if (!publish_frame()) return 1;
  }
  std::printf("PF004 published 5 frames mode=%s\n", ModeName(mode));
  if (loop) {
    std::printf("PF004 loop active mode=%s\n", ModeName(mode));
    std::fflush(stdout);
    for (;;) {
      usleep(100000);
      if (!publish_frame()) return 1;
    }
  }
  return 0;
}
