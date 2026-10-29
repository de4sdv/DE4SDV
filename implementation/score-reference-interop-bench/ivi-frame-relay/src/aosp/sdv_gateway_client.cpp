#include "aosp/sdv_gateway_client.hpp"

#include <android/binder_process.h>
#include <libsdvgatewayclient.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>

namespace de4sdv::ivi_frame_relay {

namespace {

static_assert(ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE == kSubscriberFlagNone,
              "the relay subscribes with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE");
static_assert(ASDVGateway_StatusCode_OK == kGatewayOk, "status code OK");
static_assert(ASDVGateway_StatusCode_UNAVAILABLE == kGatewayUnavailable, "status code UNAVAILABLE");
static_assert(ASDVGateway_StatusCode_DATA_LOSS == kGatewayDataLoss, "status code DATA_LOSS");

constexpr std::int32_t kFailedPrecondition = ASDVGateway_StatusCode_FAILED_PRECONDITION;
constexpr std::int32_t kInternal = ASDVGateway_StatusCode_INTERNAL;

// The sink of the client; the callbacks run on binder threads.
std::atomic<GatewayNotificationSink*> g_sink{nullptr};

// A status with a buffer for its error message.
struct Status {
  char message[512] = {};
  ASDVGateway_Status_t status{};

  Status() {
    status.statusCode = ASDVGateway_StatusCode_OK;
    status.errorMessage = message;
    status.maxErrorMessageSize = sizeof(message);
  }
  Status(const Status&) = delete;
  Status& operator=(const Status&) = delete;
};

GatewayResult Result(ASDVGateway_StatusCode_t code, const Status& status) {
  return GatewayResult{static_cast<std::int32_t>(code), std::string{status.message}};
}

// The options refuse a name that does not fit, so nothing is cut here.
void Fill(const std::string& value, char* destination, std::size_t capacity) {
  std::strncpy(destination, value.c_str(), capacity - 1);
  destination[capacity - 1] = '\0';
}

void* Tag(std::uint64_t generation) { return reinterpret_cast<void*>(static_cast<std::uintptr_t>(generation)); }

std::uint64_t Generation(void* user_data) {
  return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(user_data));
}

void OnClientNotification(ASDVGateway_ClientNotificationType_t type, void* user_data) {
  GatewayNotificationSink* sink = g_sink.load();
  if (sink == nullptr) {
    return;
  }
  GatewayNotification notification;
  notification.kind = type == ASDVGateway_ClientNotificationType_Disconnected
                          ? GatewayNotificationKind::kDisconnected
                          : GatewayNotificationKind::kOtherClientNotification;
  notification.client_generation = Generation(user_data);
  notification.raw_type = static_cast<std::int32_t>(type);
  sink->Notify(notification);
}

void OnSubscriptionNotification(const ASDVGateway_SubscriptionNotificationData_t* data, void* user_data) {
  GatewayNotificationSink* sink = g_sink.load();
  if (sink == nullptr || data == nullptr) {
    return;
  }
  GatewayNotification notification;
  switch (data->notificationType) {
    case ASDVGateway_SubscriptionNotificationType_DataAvailable:
      notification.kind = GatewayNotificationKind::kDataAvailable;
      break;
    case ASDVGateway_SubscriptionNotificationType_PublicationDestroyed:
      notification.kind = GatewayNotificationKind::kPublicationDestroyed;
      break;
    default:
      notification.kind = GatewayNotificationKind::kOtherSubscriptionNotification;
      break;
  }
  notification.subscription_generation = Generation(user_data);
  notification.publication_id = data->publication.publicationId;
  notification.raw_type = static_cast<std::int32_t>(data->notificationType);
  sink->Notify(notification);
}

}  // namespace

SdvGatewayClient::SdvGatewayClient() {
  ABinderProcess_setThreadPoolMaxThreadCount(1);
  ABinderProcess_startThreadPool();
}

SdvGatewayClient::~SdvGatewayClient() {
  if (client_ != nullptr) {
    (void)Destroy();
  }
  g_sink.store(nullptr);
}

GatewayResult SdvGatewayClient::Create(std::uint64_t client_generation, const SubjectIdentity& subject,
                                       GatewayNotificationSink& sink) {
  if (client_ != nullptr) {
    return GatewayResult{kFailedPrecondition, "a client exists"};
  }
  g_sink.store(&sink);
  Status status;
  ASDVGateway_Client* client = nullptr;
  ASDVGateway_StatusCode_t code = ASDVGateway_Client_new(&client, &status.status);
  if (code != ASDVGateway_StatusCode_OK) {
    return Result(code, status);
  }
  if (client == nullptr) {
    return GatewayResult{kInternal, "ASDVGateway_Client_new gave no client"};
  }
  code = ASDVGateway_Client_setClientNotificationCallback(client, OnClientNotification, Tag(client_generation),
                                                          &status.status);
  if (code == ASDVGateway_StatusCode_OK) {
    ASDVGateway_InitCommsParams_t init{};
    Fill(subject.package, init.packageName, sizeof(init.packageName));
    Fill(subject.bundle, init.serviceBundleName, sizeof(init.serviceBundleName));
    Fill(subject.instance, init.serviceInstanceName, sizeof(init.serviceInstanceName));
    code = ASDVGateway_Client_initComms(client, &init, &status.status);
  }
  if (code != ASDVGateway_StatusCode_OK) {
    GatewayResult failed = Result(code, status);
    Status cleanup;
    (void)ASDVGateway_Client_setClientNotificationCallback(client, nullptr, nullptr, &cleanup.status);
    (void)ASDVGateway_Client_delete(client, &cleanup.status);
    return failed;
  }
  client_ = client;
  return Result(code, status);
}

GatewayResult SdvGatewayClient::Destroy() {
  if (client_ == nullptr) {
    return GatewayResult{};
  }
  Status cleared;
  (void)ASDVGateway_Client_setClientNotificationCallback(client_, nullptr, nullptr, &cleared.status);
  Status status;
  const ASDVGateway_StatusCode_t code = ASDVGateway_Client_delete(client_, &status.status);
  client_ = nullptr;
  return Result(code, status);
}

GatewayResult SdvGatewayClient::Subscribe(std::uint64_t subscription_generation, const PublicationName& publication,
                                          PublicationMetadata* metadata) {
  if (client_ == nullptr) {
    return GatewayResult{kFailedPrecondition, "no client"};
  }
  ASDVGateway_SubscribeToPublicationByNameParams_t params{};
  Fill(publication.vm, params.sdvVmName, sizeof(params.sdvVmName));
  Fill(publication.package, params.packageName, sizeof(params.packageName));
  Fill(publication.bundle, params.serviceBundleName, sizeof(params.serviceBundleName));
  Fill(publication.unit, params.serviceUnitName, sizeof(params.serviceUnitName));
  ASDVGateway_Subscriber_Options_t options{};
  options.flags = ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE;
  options.minIntervalMs = 0;
  ASDVGateway_PublicationMetadata_t out{};
  Status status;
  const ASDVGateway_StatusCode_t code = ASDVGateway_Client_subscribeToPublicationByName(
      client_, &params, &options, OnSubscriptionNotification, Tag(subscription_generation), &out, &status.status);
  if (code == ASDVGateway_StatusCode_OK) {
    metadata->publication_id = out.publicationId;
    metadata->message_size_bytes = out.messageSizeBytes;
    metadata->message_count = out.messageCount;
    metadata->subscriber_flags = options.flags;
  }
  return Result(code, status);
}

GatewayResult SdvGatewayClient::Unsubscribe(std::int32_t publication_id) {
  if (client_ == nullptr) {
    return GatewayResult{kFailedPrecondition, "no client"};
  }
  Status cleared;
  (void)ASDVGateway_Client_setNotificationCallbackForPublicationId(client_, publication_id, nullptr, nullptr,
                                                                   &cleared.status);
  Status status;
  const ASDVGateway_StatusCode_t code =
      ASDVGateway_Client_unsubscribeFromPublication(client_, publication_id, &status.status);
  return Result(code, status);
}

ReadResult SdvGatewayClient::Read(std::int32_t publication_id, std::uint8_t* buffer, std::size_t capacity) {
  ReadResult result;
  if (client_ == nullptr) {
    result.outcome = ReadOutcome::kFailed;
    result.status = GatewayResult{kFailedPrecondition, "no client"};
    return result;
  }
  const auto bytes = static_cast<std::uint32_t>(
      capacity > std::numeric_limits<std::uint32_t>::max() ? std::numeric_limits<std::uint32_t>::max() : capacity);
  std::uint32_t count = 0;
  Status status;
  const ASDVGateway_StatusCode_t code =
      ASDVGateway_Client_readAvailableMessages(client_, publication_id, buffer, bytes, &count, &status.status);
  result.status = Result(code, status);
  if (code == ASDVGateway_StatusCode_OK) {
    result.outcome = count > 0U ? ReadOutcome::kMessages : ReadOutcome::kNoMessage;
    result.count = count;
  } else if (code == ASDVGateway_StatusCode_UNAVAILABLE) {
    result.outcome = ReadOutcome::kNoMessage;
  } else if (code == ASDVGateway_StatusCode_DATA_LOSS) {
    result.outcome = ReadOutcome::kDataLoss;  // the buffer may hold dirty data: not used
  } else {
    result.outcome = ReadOutcome::kFailed;
  }
  return result;
}

}  // namespace de4sdv::ivi_frame_relay
