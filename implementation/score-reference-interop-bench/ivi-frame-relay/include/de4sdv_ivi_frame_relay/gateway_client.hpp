// The narrow interface of the DE4SDV IVI frame relay to the SDV Gateway on
// IVI: the subset of libsdvgatewayclient, the C API of
// sdv_gateway/libsdvgatewayclient/include/libsdvgatewayclient.h of AOSP
// android17-release (manifest ad156f32), that the relay uses.
//
// Two implementations exist. The AOSP adapter
// (src/aosp/sdv_gateway_client.cpp) calls the C API; only an AOSP build
// compiles it, so the DE4SDV CI does not. The fake of the tests
// (test/fake_gateway_client.hpp) stands in for it, so CI builds and tests
// all the rest. The gateway worker (gateway_worker.hpp) makes every call, on
// its own thread.
//
// The interface holds what the relay needs and no more: create the one
// client of the process, initialize it, subscribe by name with
// ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE, read, unsubscribe, destroy. It has no call that publishes, offers or calls a
// service: the relay sends nothing to the host or the SDV Core VM. Only the
// SDV Gateway on IVI exchanges subscription control with the SDV Core VM
// for it.

#ifndef DE4SDV_IVI_FRAME_RELAY_GATEWAY_CLIENT_HPP
#define DE4SDV_IVI_FRAME_RELAY_GATEWAY_CLIENT_HPP

#include <cstddef>
#include <cstdint>
#include <string>

namespace de4sdv::ivi_frame_relay {

// Values of ASDVGateway_StatusCode_t that the relay acts on; the adapter
// checks them against the C API at compile time.
constexpr std::int32_t kGatewayOk = 0;
constexpr std::int32_t kGatewayUnavailable = 14;
constexpr std::int32_t kGatewayDataLoss = 15;

// The name of a status code as the C API spells it, for example "NOT_FOUND";
// "UNLISTED" for a value that the header does not list.
const char* GatewayStatusName(std::int32_t code) noexcept;

struct GatewayResult {
  std::int32_t code{kGatewayOk};
  std::string text;  // the error message of the status; empty when the library gave none
  bool ok() const noexcept { return code == kGatewayOk; }
};

// The relay's own identity for initComms. Its ACL names this subject.
struct SubjectIdentity {
  std::string package;
  std::string bundle;
  std::string instance;
};

// The broker's publication of the frame topic, by name.
struct PublicationName {
  std::string vm;
  std::string package;
  std::string bundle;
  std::string unit;
};

// The subscriber flag of every subscription of the relay:
// ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE. The relay reads only the
// messages published after its subscription, never the last one before it.
constexpr std::uint64_t kSubscriberFlagNone = 0;

struct PublicationMetadata {
  std::int32_t publication_id{0};
  std::uint32_t message_size_bytes{0};  // the slot size
  std::uint32_t message_count{0};       // the slots of the publication's queue
  std::uint64_t subscriber_flags{kSubscriberFlagNone};
};

enum class ReadOutcome : std::uint8_t {
  kMessages,   // OK: count slots in the buffer
  kNoMessage,  // UNAVAILABLE: nothing to read
  kDataLoss,   // DATA_LOSS: the queue dropped messages; the buffer is not used
  kFailed,     // any other status
};

struct ReadResult {
  ReadOutcome outcome{ReadOutcome::kNoMessage};
  std::uint32_t count{0};
  GatewayResult status;
};

enum class GatewayNotificationKind : std::uint8_t {
  kDataAvailable,
  kPublicationDestroyed,
  kDisconnected,
  kOtherClientNotification,        // RootCertsChanged, RpcAvailabilityChanged, or an unlisted type
  kOtherSubscriptionNotification,  // an unlisted subscription notification type
};

const char* ToText(GatewayNotificationKind kind) noexcept;

struct GatewayNotification {
  GatewayNotificationKind kind{GatewayNotificationKind::kDataAvailable};
  // The generation of the client or of the subscription that the
  // notification belongs to, so a late one of an old client or an old
  // subscription is told apart from one of the current.
  std::uint64_t client_generation{0};
  std::uint64_t subscription_generation{0};
  std::int32_t publication_id{0};
  std::int32_t raw_type{0};  // the notification type of the C API
};

// Takes the notifications of the library, on the library's own threads. It
// must return at once, and it never calls the client.
class GatewayNotificationSink {
 public:
  virtual ~GatewayNotificationSink() = default;
  virtual void Notify(const GatewayNotification& notification) noexcept = 0;
};

class GatewayClient {
 public:
  virtual ~GatewayClient() = default;
  // ASDVGateway_Client_new and the client notification callback. The
  // notifications of this client and of its subscriptions go to sink. The
  // library allows one client per process, also after the first one was
  // deleted (libsdvgatewayclient.h:473-475). So *created tells whether
  // ASDVGateway_Client_new succeeded: once it has, the client belongs to this
  // process for good, also when the result is a failure of the callback, and
  // the worker never calls NewClient again.
  virtual GatewayResult NewClient(std::uint64_t client_generation, GatewayNotificationSink& sink,
                                  bool* created) = 0;
  // initComms with the subject, on the client of NewClient.
  virtual GatewayResult InitComms(const SubjectIdentity& subject) = 0;
  // Clears the client notification callback and deletes the client; only at
  // the stop of the relay.
  virtual GatewayResult Destroy() = 0;
  // subscribeToPublicationByName with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE
  // and a notification interval of 0. Fills metadata on success.
  virtual GatewayResult Subscribe(std::uint64_t subscription_generation, const PublicationName& publication,
                                  PublicationMetadata* metadata) = 0;
  // Clears the notification callback of the subscription and unsubscribes.
  virtual GatewayResult Unsubscribe(std::int32_t publication_id) = 0;
  // readAvailableMessages into buffer, at most capacity / message size slots.
  virtual ReadResult Read(std::int32_t publication_id, std::uint8_t* buffer, std::size_t capacity) = 0;
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_GATEWAY_CLIENT_HPP
