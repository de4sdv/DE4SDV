// The actuation adapter's shell: it moves the two inputs into the core, applies
// what the core accepts through the simulator client and writes the records.
// No middleware and no simulator code here: actuation_adapter_main.cpp feeds it
// from mw::com, and simulator_client.h is a plain function interface, so the
// host's tests drive the shell against a fake client.
//
//   OnSnapshot()  the client's thread, once per world snapshot;
//   OnCommand()   the mw::com receive thread, once per driving command.
//
// One mutex serializes both, the core call, the client call and the records.
// A rejected command is logged (in.driving_command, drop) and nothing is
// applied in its place: the simulator keeps the last valid control (PSR
// DrivingCommandActuationAdapter). An accepted command is applied once, at its
// arrival; nothing is applied on a world snapshot.
#pragma once

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>

#include "actuation_core.h"
#include "run_log.h"
#include "simulator_client.h"

namespace de4sdv::driver_assistance::actuation {

// Numbers the records of one log (the record's own seq).
class RecordWriter {
 public:
  explicit RecordWriter(RecordSink* sink) : sink_(sink) {}
  void Write(const std::string& event, const std::string& data_json) {
    sink_->Write(event, ++sequence_, data_json);
  }

 private:
  RecordSink* sink_;
  std::atomic<std::uint64_t> sequence_{0};
};

// The Ackermann control as the client receives it: the core's doubles as floats.
simulator::AppliedAckermannControl ToApplied(const AckermannControl& control);

class AdapterShell {
 public:
  explicit AdapterShell(RecordWriter* records) : records_(records) {}

  void OnSnapshot(const simulator::SnapshotSample& sample);
  void OnCommand(const DrivingCommandEventPayload& command, double arrivalMonoS);

  // For the tests and the stop record.
  std::uint64_t AppliedCount() const;
  std::uint64_t DroppedCount() const;

 private:
  RecordWriter* records_;
  mutable std::mutex mutex_;
  ActuationCore core_;
  std::uint64_t applied_ = 0;
  std::uint64_t dropped_ = 0;
  bool ego_absent_logged_ = false;
};

// Registers shell.OnSnapshot as the simulator client's snapshot handler.
bool AttachToSimulator(AdapterShell* shell, std::string* error);

}  // namespace de4sdv::driver_assistance::actuation
