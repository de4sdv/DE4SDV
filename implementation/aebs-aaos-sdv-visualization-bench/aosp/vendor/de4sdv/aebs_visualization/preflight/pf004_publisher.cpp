// DE4SDV INC-AEBS-010 PF-004 probe: native publisher via SDV Gateway Data Tunnel.
// Bench-only probe: initComms as de4sdv.aebs_visualization, create a publication,
// publish five fixed 256-byte payloads. No product claim.
//
// v2: starts the NDK Binder thread pool before Client_new (the official
// libsdvgatewayclient checks this first and returns FAILED_PRECONDITION
// "Binder thread pool is not started" otherwise), and prints
// status.errorMessage for every failure so the cause is observable instead
// of a bare numeric code.

#include <libsdvgatewayclient.h>

#include <android/binder_process.h>

#include <cstdio>
#include <cstring>
#include <unistd.h>

namespace {

void Fill(const char* value, char* dest, size_t size) {
  std::strncpy(dest, value, size - 1);
  dest[size - 1] = '\0';
}

const char* Err(const ASDVGateway_Status_t& status) {
  return status.errorMessage != nullptr ? status.errorMessage : "(no message)";
}

}  // namespace

int main() {
  // Required before any binder client: without the pool the gateway client
  // refuses to construct (FAILED_PRECONDITION "Binder thread pool is not
  // started").
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
  Fill("de4sdv.aebs_visualization", params.unitType.sdvPackageName,
       sizeof(params.unitType.sdvPackageName));
  Fill("AebsVisualization", params.unitType.serviceBundleName,
       sizeof(params.unitType.serviceBundleName));
  Fill("VisualizationFrame", params.unitType.unitTypeName,
       sizeof(params.unitType.unitTypeName));
  params.publisherUnitMetadata.version = 1;
  params.publisherUnitMetadata.messageSizeBytes = 256;
  params.publisherUnitMetadata.messageCount = 16;

  ASDVGateway_PublicationMetadata_t metadata{};
  if (ASDVGateway_Client_createPublication(client, &params, &metadata, &status) !=
      ASDVGateway_StatusCode_OK) {
    std::printf("PF004 createPublication failed: %d %s\n",
                static_cast<int>(status.statusCode), Err(status));
    return 1;
  }
  std::printf("PF004 createPublication ok id=%d\n", metadata.publicationId);

  uint8_t payload[256];
  std::memset(payload, 0xAB, sizeof(payload));
  for (int i = 0; i < 5; ++i) {
    payload[0] = static_cast<uint8_t>(i);
    if (ASDVGateway_Client_publishMessages(client, payload, sizeof(payload),
                                           metadata.publicationId, &status) !=
        ASDVGateway_StatusCode_OK) {
      std::printf("PF004 publishMessages failed: %d %s\n",
                  static_cast<int>(status.statusCode), Err(status));
      return 1;
    }
  }
  std::printf("PF004 published 5 frames\n");
  if (loop) {
    for (int burst = 6;; ++burst) {
      usleep(500000);
      payload[0] = static_cast<uint8_t>(burst);
      if (ASDVGateway_Client_publishMessages(client, payload, sizeof(payload),
                                             metadata.publicationId, &status) !=
          ASDVGateway_StatusCode_OK) {
        std::printf("PF004 publishMessages failed: %d\n",
                    static_cast<int>(status.statusCode));
        return 1;
      }
    }
  }
  return 0;
}
