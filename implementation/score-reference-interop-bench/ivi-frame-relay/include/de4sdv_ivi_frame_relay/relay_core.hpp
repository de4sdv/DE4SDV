// Pure core of the DE4SDV IVI frame relay: the subscription phase, the checks
// of each slot, the discard policy, the loopback client of the HMI ingress,
// the ingress trigger and the clock controls. It runs on the main thread. The
// gateway worker's events and the shell's socket events come in as calls,
// and the core decides for every slot whether it goes to the client.
//
// Subscription phase (relaySubscriptionPhaseDiscardRule): the HMI
// application counts as subscribed while two conditions hold: the relay
// holds a subscription, through the SDV Gateway on IVI, to the broker's
// publication of the frame topic, and the ingress is the one client of the
// relay's loopback server. A phase starts when the second of the two starts
// to hold, at CLOCK_REALTIME of the IVI VM, and ends when one of them ends.
// The relay is not subscribed at its start. A second client is refused while
// one is connected: it is not served and starts no phase. Outside a phase
// every slot is read and dropped; the relay holds no frame for later
// delivery. The ingress connection stays open while the publication is
// unavailable, so the ingress keeps its last accepted sequence.
//
// Phase ends: PublicationDestroyed, Disconnected and the 3 s timeout end the
// subscription. Such an end while the ingress stays connected is a delivery
// failure of the layer, not an unsubscription of the HMI application, and its
// phase_end line says so (layer_caused). The core logs and counts every
// phase start and every phase end. A DATA_LOSS status of a read is a gap
// (GAP-MW-037): it is counted and logged, and the phase goes on.
//
// The checks of each slot, in this order, each with its own drop reason: the
// strict parse of the broker's wrapper (broker_wrapper.hpp); the payload
// size, at most 2048 bytes (the 4-byte prefix and a frame of up to 2044
// bytes); the payload's own length prefix; the two frame fields
// (frame_fields.hpp); outside a phase, not_subscribed or no_client; in a
// phase, the discard policy (discard_policy.hpp). A slot that passes goes to
// the client as the payload of the wrapper, prefix and frame, with no byte
// changed (REQ-MW-015). So every slot ends in exactly one outcome, delivered
// or dropped with one reason: messages_read equals frames_delivered plus the
// sum of the drops. Every drop gives a frame line with its reason; a served
// frame gives one for the first five of a phase, or always with --log-frames.
//
// Loss of the gateway client: the library allows one client per process
// (libsdvgatewayclient.h:473-475). So when the worker reports the client as
// lost (Disconnected, or a failed initComms), the core logs
// gateway_client_lost with the stage and the status, ends the phase as a
// phase end of the layer, and asks the shell to end the process with
// kExitGatewayClientLost. init starts the relay again as a new process, and
// that start triggers the ingress again.
//
// Start diagnostic: when no subscription has succeeded 30 s after the start,
// the core logs subscription_start_diagnostic once. A subject without an ACL
// gets "No publication service unit found", the reply to a missing
// publication too. So the line names a likely fault of the ACL or of the
// mapping when a client exists, and of the gateway client when none was
// created. From then on the worker tries every 10 s.
//
// Clock controls for ASM-MW-030: the core reads CLOCK_REALTIME minus
// CLOCK_MONOTONIC at every event, and the shell gives it an event at least
// every 100 ms. A slew moves both clocks alike, so this difference changes
// only when the realtime clock is stepped or across a suspend. A change of
// 1 ms or more between two readings is a clock step: it is logged, and the
// phase it falls in is marked. The start, each phase start and each status
// line log the difference. Each served frame gives its receipt time minus
// its frame_timestamp_ns, and the phase end and the status lines log the
// minimum and the maximum of that value in the phase. The minimum bounds the
// offset from one side only: a negative minimum shows an IVI VM clock that is
// behind the host clock by at least that much; a clock ahead looks like
// latency. It is no bounding control.
//
// Start of the HMI ingress: the ingress is a oneshot service. It exits when
// its connect fails or its stream closes, and init does not start a service
// again while it runs or before init has reaped it. So the core sets the
// start property of the ingress to 0 and then 1 once the loopback server
// listens. When this start of the relay follows the end of an old relay, its
// old ingress may still run or not be reaped yet, and that trigger does
// nothing. So, until the first client of this relay process connects, the
// core repeats the trigger every 1 s, at most 10 times, and logs
// ingress_trigger_gave_up 1 s after the last try. After the first client,
// the core never triggers the ingress again in this process: an ingress that
// exits by itself or is stopped on purpose stays down. One case differs, the
// relay's reading, not a value of the model: when the relay itself closes the
// ingress stream after a write stall, the ingress exits because of the relay,
// so the trigger starts again as after a start of the relay. Each try gives
// one log line.
//
// Gateway calls: the core reports a call of the worker that has run for 10 s
// (gateway_call_stalled) and its return (gateway_call_returned), from the
// GatewayCallMonitor; the 10 s are the relay's reading, not a value of the
// model. It never waits for the worker.

#ifndef DE4SDV_IVI_FRAME_RELAY_RELAY_CORE_HPP
#define DE4SDV_IVI_FRAME_RELAY_RELAY_CORE_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

#include "de4sdv_ivi_frame_relay/broker_wrapper.hpp"
#include "de4sdv_ivi_frame_relay/discard_policy.hpp"
#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/frame_fields.hpp"
#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"

namespace de4sdv::ivi_frame_relay {

struct RelayConfig {
  // One frame line per served frame. Every dropped slot gives its line
  // anyway, with its reason; without this flag only the first five served
  // frames of a phase give one.
  bool log_frames{false};
  // The system property that starts the HMI ingress; empty: no trigger.
  std::string ingress_start_property;
  // The time after which a gateway call counts as stalled; the tests use less.
  std::int64_t gateway_call_stall_ns{kGatewayCallStallNs};
};

// The exit code of a process that lost its gateway client; init starts the
// relay again. Codes 2 (a refused option) and 3 (no loopback server) end a
// start; 0 is a stop.
constexpr int kExitGatewayClientLost = 4;

// The largest payload: the 4-byte prefix and a frame of up to 2044 bytes in
// the 2048-byte sample of the S-CORE frame event.
constexpr std::size_t kMaxPayloadBytes = 2048;
constexpr std::int64_t kClockStepThresholdNs = 1 * kNanosecondsPerMillisecond;
constexpr std::uint64_t kFirstFramesLoggedPerPhase = 5;
constexpr std::int64_t kIngressRetriggerPeriodNs = 1 * kNanosecondsPerSecond;
constexpr std::uint64_t kIngressRetriggerLimit = 10;
// A repeated read failure gives at most one log line per second.
constexpr std::int64_t kRepeatedLogPeriodNs = 1 * kNanosecondsPerSecond;

enum class ForwardResult : std::uint8_t {
  kWritten,
  kFailed,   // the write failed or stalled past its timeout; the shell closed the client
  kStopped,  // a stop request ended a blocked write; the shell closed the client
};

// The loopback client of the HMI ingress, implemented by the shell.
class FrameSink {
 public:
  virtual ~FrameSink() = default;
  // Writes the whole payload or closes the client.
  virtual ForwardResult Forward(const std::uint8_t* payload, std::size_t size) = 0;
};

// The process at the other end of a loopback connection, as far as the
// shell can tell. SO_PEERCRED gives no credentials on a TCP socket, so the
// shell finds the client's socket in /proc/net/tcp (its uid and inode) and
// the process that holds that inode in /proc/<pid>/fd.
struct PeerIdentity {
  std::uint16_t port{0};  // the client's port on 127.0.0.1
  bool uid_known{false};
  std::int64_t uid{-1};
  bool pid_known{false};
  std::int64_t pid{-1};
  const char* source{"none"};  // "proc_net_tcp", or "none"
};

// Sets a system property, implemented by the shell: on Android with
// __system_property_set; elsewhere it only logs the property.
class PropertySetter {
 public:
  virtual ~PropertySetter() = default;
  virtual bool SetProperty(const Clock& now, const std::string& name, const std::string& value) = 0;
};

enum class DropReason : std::uint8_t {
  kWrapperOuterVarintInvalid,
  kWrapperOuterLengthExceedsSlot,
  kWrapperFieldMissing,
  kWrapperTagNotBytesField1,
  kWrapperInnerVarintInvalid,
  kWrapperFieldExceedsMessage,
  kWrapperBytesAfterField,
  kWrapperFillNotZero,
  kPayloadTooLarge,
  kPayloadTooShort,
  kLengthPrefixMismatch,
  kFrameUnreadable,
  kNotSubscribed,  // outside a phase: no subscription
  kNoClient,       // outside a phase: subscribed, but no client
  kFieldNotPositive,
  kOlderThanPhase,
  kCopyInPhase,
  kClientWriteFailed,
  kRelayStop,  // a stop request ended the write of this frame
};

constexpr std::size_t kDropReasonCount = 19;

const char* ToText(DropReason reason) noexcept;

struct RelayCounters {
  std::uint64_t messages_read{0};
  std::uint64_t frames_delivered{0};
  std::array<std::uint64_t, kDropReasonCount> drops{};
  std::uint64_t data_loss_reads{0};
  std::uint64_t read_failures{0};
  std::uint64_t clients_accepted{0};
  std::uint64_t clients_refused{0};
  std::uint64_t clients_lost{0};
  std::uint64_t phases_started{0};
  std::uint64_t phases_ended{0};
  std::uint64_t phases_ended_by_layer{0};
  std::uint64_t clock_steps{0};
  std::uint64_t ingress_triggers{0};
  std::uint64_t client_create_attempts{0};
  std::uint64_t client_create_failures{0};
  std::uint64_t clients_destroyed{0};
  std::uint64_t gateway_client_losses{0};
  std::uint64_t subscribe_attempts{0};
  std::uint64_t subscribe_failures{0};
  std::uint64_t subscriptions{0};
  std::uint64_t ended_publication_destroyed{0};
  std::uint64_t ended_disconnected{0};
  std::uint64_t ended_silence_timeout{0};
  std::uint64_t unsubscribe_failures{0};
  std::uint64_t notifications_not_acted_on{0};
  std::uint64_t gateway_calls_stalled{0};

  std::uint64_t frames_dropped() const noexcept;
};

class RelayCore final {
 public:
  RelayCore(const RelayConfig& config, FrameSink& sink, FrameDiscardPolicy& policy, EventLog& log,
            PropertySetter* properties = nullptr, GatewayCallMonitor* monitor = nullptr);

  // The relay's start: the time of the start diagnostic counts from here.
  void OnStart(const Clock& now);
  // The loopback server listens: the first trigger of the ingress.
  void OnListening(const Clock& now);
  void OnWorkerEvent(const WorkerEvent& event);
  // A loopback client connected. false: another client is connected, so the
  // shell closes the new one; it is not served and starts no phase. Both
  // lines name the peer process.
  bool OnClientAccepted(const Clock& now, const PeerIdentity& peer = PeerIdentity{});
  void OnClientDisconnected(const Clock& now);
  void OnTick(const Clock& now);
  // Reads the offset of the two clocks; every event calls it.
  void ObserveClock(const Clock& now);
  void Stop(const Clock& now);

  std::int64_t NextDeadline() const noexcept;
  // The core asks the shell to end the process: the gateway client is lost.
  bool exit_requested() const noexcept { return exit_requested_; }
  int exit_code() const noexcept { return exit_code_; }
  bool subscribed() const noexcept { return subscribed_; }
  bool client_connected() const noexcept { return client_connected_; }
  bool in_phase() const noexcept { return in_phase_; }
  std::int64_t phase_start_realtime_ns() const noexcept { return phase_start_realtime_ns_; }
  const RelayCounters& counters() const noexcept { return counters_; }
  // A status line with every counter.
  LogRecord Status(const char* event) const;

 private:
  void UpdatePhase(const Clock& now, const char* cause, bool layer_caused);
  void OnMessage(const WorkerEvent& event);
  void Drop(const WorkerEvent& event, DropReason reason, std::size_t payload_bytes, const FrameFields* fields,
            const WrapperParse* wrapper = nullptr);
  void LogFrame(const WorkerEvent& event, const char* verdict, std::size_t payload_bytes, const FrameFields* fields,
                const WrapperParse* wrapper = nullptr);
  void LogStatus(LogRecord& record, const GatewayResult& status) const;
  bool IngressTriggerDue() const noexcept;
  void TriggerIngress(const Clock& now, const char* reason);
  // The relay itself closed the ingress stream, so the ingress exits: the
  // trigger starts again as after a start of the relay.
  void RearmIngressTrigger(const Clock& now);
  void LoseClient(const WorkerEvent& event, const char* reason, const char* cause);
  void CheckStartDiagnostic(const Clock& now);
  void CheckGatewayCalls(const Clock& now);

  RelayConfig config_;
  FrameSink& sink_;
  FrameDiscardPolicy& policy_;
  EventLog& log_;
  PropertySetter* properties_;
  GatewayCallMonitor* monitor_;

  bool started_{false};
  bool exit_requested_{false};
  int exit_code_{0};
  Clock start_{};
  bool start_diagnostic_done_{false};
  bool client_ever_created_{false};
  bool has_client_{false};
  bool ever_subscribed_{false};
  GatewayResult last_failure_;
  const char* last_failure_stage_{""};

  bool subscribed_{false};
  std::int64_t subscribed_since_realtime_ns_{0};
  std::uint64_t subscription_{0};
  std::int32_t publication_id_{0};
  bool client_connected_{false};
  std::int64_t client_since_realtime_ns_{0};
  bool in_phase_{false};
  std::int64_t phase_start_realtime_ns_{0};
  std::uint64_t phase_clock_steps_{0};
  std::uint64_t phase_served_{0};
  bool phase_receipt_known_{false};
  std::int64_t phase_receipt_min_ns_{0};
  std::int64_t phase_receipt_max_ns_{0};

  bool clock_seen_{false};
  std::int64_t clock_offset_ns_{0};
  bool read_failure_logged_{false};
  std::int64_t read_failure_logged_ns_{0};
  std::uint64_t read_failures_suppressed_{0};

  bool listening_{false};
  bool first_client_seen_{false};
  bool ingress_trigger_gave_up_{false};
  std::int64_t next_ingress_trigger_ns_{0};
  std::uint64_t ingress_retriggers_{0};
  RelayCounters counters_{};
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_RELAY_CORE_HPP
