#include "fake_simulator_client.h"

#include <utility>

namespace de4sdv::driver_assistance::actuation::simulator {
namespace {

struct State {
  std::vector<AppliedAckermannControl> applied;
  bool applyFails = false;
  SnapshotHandler handler;
  fake::Calls calls;
};

State& Fake() {
  static State state;
  return state;
}

}  // namespace

bool Connect(const ClientOptions& options, ClientInfo* info, std::string* error) {
  ++Fake().calls.connect;
  if (options.heroRoleName.empty()) {
    if (error != nullptr) *error = "no hero";
    return false;
  }
  if (info != nullptr) {
    info->clientVersion = "fake";
    info->serverVersion = "fake";
    info->heroActorId = 7;
    info->heroTypeId = "vehicle.fake";
  }
  return true;
}

bool StartSnapshots(SnapshotHandler handler, std::string*) {
  ++Fake().calls.startSnapshots;
  Fake().handler = std::move(handler);
  return true;
}

void StopSnapshots() {
  ++Fake().calls.stopSnapshots;
  Fake().handler = nullptr;
}

bool ApplyAckermannControl(const AppliedAckermannControl& control, std::string* error) {
  ++Fake().calls.apply;
  if (Fake().applyFails) {
    if (error != nullptr) *error = "fake refusal";
    return false;
  }
  Fake().applied.push_back(control);
  return true;
}

void Disconnect() { ++Fake().calls.disconnect; }

namespace fake {

std::vector<AppliedAckermannControl>& Applied() { return Fake().applied; }
void SetApplyFails(bool fails) { Fake().applyFails = fails; }
bool EmitSnapshot(const SnapshotSample& sample) {
  if (!Fake().handler) return false;
  Fake().handler(sample);
  return true;
}
void Reset() { Fake() = State{}; }
const Calls& CallCounts() { return Fake().calls; }

}  // namespace fake
}  // namespace de4sdv::driver_assistance::actuation::simulator
