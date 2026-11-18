// A fake of simulator_client.h for the host's tests: it records every control
// it is given, can refuse one, and lets a test emit world snapshots through the
// handler that StartSnapshots registered. Not a model of CARLA.
#pragma once

#include <vector>

#include "simulator_client.h"

namespace de4sdv::driver_assistance::actuation::simulator::fake {

std::vector<AppliedAckermannControl>& Applied();
void SetApplyFails(bool fails);
// Calls the registered handler; returns false when none is registered.
bool EmitSnapshot(const SnapshotSample& sample);
void Reset();

// How often each function was called.
struct Calls {
  int connect = 0;
  int startSnapshots = 0;
  int stopSnapshots = 0;
  int apply = 0;
  int disconnect = 0;
};
const Calls& CallCounts();

}  // namespace de4sdv::driver_assistance::actuation::simulator::fake
