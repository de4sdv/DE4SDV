// DE4SDV INC-AEBS-010 PF-004 probe: native publisher via SDV Gateway Data Tunnel.
// Bench-only probe: initComms as de4sdv.aebs_visualization, create a publication,
// publish five fixed 256-byte payloads. No product claim.

#include <libsdvgatewayclient.h>

#include <cstdio>
#include <cstring>

namespace {

void Fill(const char* value, char* dest, size_t size) {
  std::strncpy(dest, value, size - 1);
  dest[size - 1] = '\0';
}

}  // namespace

int main() {
  ASDVGateway_Client* client = nullptr;
  ASDVGateway_Status_t status{};
  if (ASDVGateway_Client_new(&client, &status) !=
      ASDVGateway_StatusCode_OK) {
    std::printf("PF004 client_new failed: %d\n", static_cast<int>(status.statusCode));
    return 1;
  }

  ASDVGateway_InitCommsParams_t init{};
  Fill("de4sdv.aebs_visualization", init.packageName, sizeof(init.packageName));
  Fill("aebs_visualization", init.serviceBundleName, sizeof(init.serviceBundleName));
  Fill("pf004", init.serviceInstanceName, sizeof(init.serviceInstanceName));
  if (ASDVGateway_Client_initComms(client, &init, &status) !=
      ASDVGateway_StatusCode_OK) {
    std::printf("PF004 initComms failed: %d %s\n", static_cast<int>(status.statusCode),
                status.errorMessage != nullptr ? status.errorMessage : "");
    return 1;
  }
  std::printf("PF004 initComms ok\n");

  ASDVGateway_CreatePublicationParams_t params{};
  Fill("aebs_visualization_frame", params.serviceUnitName, sizeof(params.serviceUnitName));
  Fill("de4sdv.aebs_visualization", params.unitType.sdvPackageName,
       sizeof(params.unitType.sdvPackageName));
  Fill("aebs_visualization", params.unitType.serviceBundleName,
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
                static_cast<int>(status.statusCode),
                status.errorMessage != nullptr ? status.errorMessage : "");
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
                  static_cast<int>(status.statusCode),
                  status.errorMessage != nullptr ? status.errorMessage : "");
      return 1;
    }
  }
  std::printf("PF004 published 5 frames\n");
  return 0;
}
