// Tests of the actuation adapter's shell (adapter_shell.h) against the fake
// simulator client: what is applied, what is not, and the records.
#include <cmath>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>

#include "adapter_shell.h"
#include "check.h"
#include "fake_simulator_client.h"
#include "json_lite.h"
#include "log_records.h"

using de4sdv::driver_assistance::DrivingCommandCheckValue;
using de4sdv::driver_assistance::DrivingCommandEventPayload;
using de4sdv::driver_assistance::RecordSink;
using de4sdv::driver_assistance::actuation::AdapterShell;
using de4sdv::driver_assistance::actuation::AttachToSimulator;
using de4sdv::driver_assistance::actuation::RecordWriter;
using de4sdv::driver_assistance::actuation::test::Finish;
using de4sdv::driver_assistance::json::Value;
namespace sim = de4sdv::driver_assistance::actuation::simulator;
namespace fake = de4sdv::driver_assistance::actuation::simulator::fake;

namespace {

struct Record {
  std::string event;
  std::uint64_t seq = 0;
  Value data;
};

class CaptureSink : public RecordSink {
 public:
  void Write(const std::string& event, std::uint64_t seq, const std::string& data_json) override {
    std::string error;
    Record record;
    record.event = event;
    record.seq = seq;
    record.data = Value::Parse(data_json, &error);
    parse_errors += error.empty() ? 0 : 1;
    records.push_back(record);
  }
  std::vector<Record> records;
  int parse_errors = 0;
};

// One shell on a fresh fake, with its records captured.
struct Bench {
  CaptureSink sink;
  RecordWriter writer{&sink};
  AdapterShell shell{&writer};
  Bench() { fake::Reset(); }

  std::vector<const Record*> Events(const std::string& event) const {
    std::vector<const Record*> out;
    for (const Record& r : sink.records) {
      if (r.event == event) out.push_back(&r);
    }
    return out;
  }
};

DrivingCommandEventPayload Command(std::uint32_t sequence, double issueTime,
                                   float acceleration = 0.0F, float steeringAngle = 0.0F) {
  DrivingCommandEventPayload command{};
  command.acceleration = acceleration;
  command.steeringAngle = steeringAngle;
  command.issueTime = issueTime;
  command.sequenceCount = sequence;
  command.checkValue = DrivingCommandCheckValue(command);
  return command;
}

sim::SnapshotSample Snapshot(std::uint64_t frame, double t, double v, bool ego = true) {
  sim::SnapshotSample s;
  s.frame = frame;
  s.simTimeS = t;
  s.egoPresent = ego;
  s.speedMps = v;
  return s;
}

double Num(const Record* r, const char* key) {
  const Value* v = r->data.Find(key);
  return v != nullptr ? v->AsNumber(std::numeric_limits<double>::quiet_NaN())
                      : std::numeric_limits<double>::quiet_NaN();
}
std::string Str(const Record* r, const char* key) {
  const Value* v = r->data.Find(key);
  return v != nullptr ? v->AsString("") : std::string();
}
bool Flag(const Record* r, const char* key) {
  const Value* v = r->data.Find(key);
  return v != nullptr && v->AsBool(false);
}
bool IsNull(const Record* r, const char* key) {
  const Value* v = r->data.Find(key);
  return v != nullptr && v->IsNull();
}

void TestAcceptedCommandIsAppliedAndLogged() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(249, 12.45, 5.0));
  b.shell.OnCommand(Command(1, 12.35, -1.5F, 10.0F), 100.25);
  CHECK(b.sink.parse_errors == 0);
  CHECK(fake::Applied().size() == 1);
  CHECK(b.shell.AppliedCount() == 1);
  const sim::AppliedAckermannControl& applied = fake::Applied().front();
  CHECK_EQ_D(applied.speed, 2.0F);
  CHECK_EQ_D(applied.acceleration, -1.5F);
  CHECK_EQ_D(applied.jerk, 10.0F);
  CHECK_EQ_D(applied.steerSpeed, 0.0F);
  CHECK_EQ_D(applied.steer, static_cast<float>(-10.0 * 3.14159265358979323846 / 180.0));

  // The records, in order: the snapshot, the command, the control.
  CHECK(b.sink.records.size() == 3);
  CHECK(b.sink.records[0].event == "in.world_snapshot");
  CHECK(b.sink.records[1].event == "in.driving_command");
  CHECK(b.sink.records[2].event == "out.ackermann_control");
  CHECK(b.sink.records[0].seq == 1 && b.sink.records[2].seq == 3);
  const Record* in = &b.sink.records[1];
  CHECK_EQ_D(Num(in, "seq"), 1.0);
  CHECK(Flag(in, "crc_ok"));
  CHECK_EQ_D(Num(in, "issueTime_sim_s"), 12.35);
  CHECK_EQ_D(Num(in, "newestWorldTime_sim_s"), 12.45);
  CHECK_EQ_D(Num(in, "newestWorldFrame"), 249.0);
  CHECK(Str(in, "verdict") == "accepted");
  CHECK_EQ_D(Num(in, "referenceSeq"), 0.0);
  CHECK_EQ_D(Num(in, "arrival_mono_s"), 100.25);
  const Record* out = &b.sink.records[2];
  CHECK_EQ_D(Num(out, "frame"), 249.0);
  CHECK_EQ_D(Num(out, "t_sim_s"), 12.45);
  CHECK_EQ_D(Num(out, "seq"), 1.0);
  CHECK_EQ_D(Num(out, "steer"), static_cast<double>(applied.steer));
  CHECK_EQ_D(Num(out, "steerSpeed"), 0.0);
  CHECK_EQ_D(Num(out, "speed"), 2.0);
  CHECK_EQ_D(Num(out, "acceleration"), -1.5);
  CHECK_EQ_D(Num(out, "jerk"), 10.0);
  CHECK(Str(out, "controlSource") == "actuationAdapter");
}

void TestEachRejectionIsLoggedAndNothingIsApplied() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(249, 12.45, 5.0));
  b.shell.OnCommand(Command(1, 12.35, 0.5F, 2.0F), 1.0);  // accepted
  b.shell.OnCommand(Command(1, 12.35, 0.5F, 2.0F), 1.1);  // repetition
  DrivingCommandEventPayload corrupt = Command(2, 12.35, -4.0F);
  corrupt.checkValue ^= 0x80000000u;
  b.shell.OnCommand(corrupt, 1.2);                         // corruption
  b.shell.OnCommand(Command(2, 12.30, -4.0F), 1.3);        // delay (150 ms)
  b.shell.OnCommand(Command(4, 12.45, -4.0F), 1.4);        // loss
  CHECK(fake::Applied().size() == 1);
  CHECK(fake::CallCounts().apply == 1);
  CHECK(b.shell.AppliedCount() == 1);
  CHECK(b.shell.DroppedCount() == 4);
  const auto drops = b.Events("drop");
  CHECK(drops.size() == 4);
  if (drops.size() == 4) {
    CHECK(Str(drops[0], "reason") == "repetition");
    CHECK(Str(drops[1], "reason") == "corruption");
    CHECK(Str(drops[2], "reason") == "delay");
    CHECK(Str(drops[3], "reason") == "loss");
    // The reference each decision was made against: the delayed 2 moved it.
    CHECK_EQ_D(Num(drops[0], "referenceSeq"), 1.0);
    CHECK_EQ_D(Num(drops[1], "referenceSeq"), 1.0);
    CHECK_EQ_D(Num(drops[2], "referenceSeq"), 1.0);
    CHECK_EQ_D(Num(drops[3], "seq"), 4.0);
    CHECK_EQ_D(Num(drops[3], "referenceSeq"), 2.0);
    CHECK_EQ_D(Num(drops[2], "issueTime_sim_s"), 12.30);
    CHECK_EQ_D(Num(drops[2], "newestWorldTime_sim_s"), 12.45);
  }
  const auto ins = b.Events("in.driving_command");
  CHECK(ins.size() == 5);
  if (ins.size() == 5) {
    CHECK(Str(ins[0], "verdict") == "accepted");
    for (std::size_t i = 1; i < 5; ++i) CHECK(Str(ins[i], "verdict") == "rejected");
    CHECK(!Flag(ins[2], "crc_ok"));
    CHECK(Flag(ins[3], "crc_ok"));
  }
  CHECK(b.Events("out.ackermann_control").size() == 1);
}

// After a rejection the simulator keeps the last valid control: no record, no
// call, the control the fake holds is the accepted one. Six late commands, each
// in order, each rejected.
void TestNothingIsAppliedAfterARejection() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 4.0));
  b.shell.OnCommand(Command(1, 0.50, 1.0F, -3.0F), 1.0);
  const sim::AppliedAckermannControl kept = fake::Applied().back();
  for (std::uint32_t n = 2; n <= 7; ++n) {
    b.shell.OnSnapshot(Snapshot(10 + n, 0.50 + 0.05 * n, 4.0));
    b.shell.OnCommand(Command(n, 0.30, -5.0F, 30.0F), 1.0 + n);  // 200 ms or more older
  }
  CHECK(fake::Applied().size() == 1);
  CHECK_EQ_D(fake::Applied().back().speed, kept.speed);
  CHECK_EQ_D(fake::Applied().back().steer, kept.steer);
  const auto drops = b.Events("drop");
  CHECK(drops.size() == 6);
  for (const Record* drop : drops) CHECK(Str(drop, "reason") == "delay");
  CHECK(b.Events("out.ackermann_control").size() == 1);
}

// A loss makes no later valid command fail: after a loss the command
// that reveals it is dropped and the next one is applied.
void TestAfterALossTheNextCommandIsApplied() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 4.0));
  b.shell.OnCommand(Command(1, 0.50), 1.0);
  b.shell.OnCommand(Command(3, 0.50), 1.1);  // 2 lost: 3 reveals it
  b.shell.OnCommand(Command(4, 0.50, 1.0F), 1.2);
  CHECK(fake::Applied().size() == 2);
  if (fake::Applied().size() == 2) CHECK_EQ_D(fake::Applied().back().speed, 6.0F);
  const auto drops = b.Events("drop");
  CHECK(drops.size() == 1);
  if (!drops.empty()) {
    CHECK(Str(drops[0], "reason") == "loss");
    CHECK_EQ_D(Num(drops[0], "seq"), 3.0);
    CHECK_EQ_D(Num(drops[0], "referenceSeq"), 1.0);
  }
  const auto ins = b.Events("in.driving_command");
  CHECK(ins.size() == 3);
  if (ins.size() == 3) CHECK_EQ_D(Num(ins[2], "referenceSeq"), 3.0);
}

void TestARefusedApplicationIsAnError() {
  Bench b;
  fake::SetApplyFails(true);
  b.shell.OnSnapshot(Snapshot(10, 0.50, 4.0));
  b.shell.OnCommand(Command(1, 0.50), 1.0);
  CHECK(fake::CallCounts().apply == 1);
  CHECK(b.shell.AppliedCount() == 0);
  CHECK(b.Events("out.ackermann_control").empty());
  const auto errors = b.Events("error");
  CHECK(errors.size() == 1);
  if (!errors.empty()) {
    CHECK(Str(errors[0], "what") == "ApplyAckermannControl failed");
    CHECK(Str(errors[0], "message") == "fake refusal");
  }
}

void TestANonFiniteControlIsNotSent() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 4.0));
  b.shell.OnCommand(Command(1, 0.50, std::numeric_limits<float>::quiet_NaN()), 1.0);
  CHECK(fake::CallCounts().apply == 0);
  CHECK(b.Events("out.ackermann_control").empty());
  const auto errors = b.Events("error");
  CHECK(errors.size() == 1);
  if (!errors.empty()) CHECK(Str(errors[0], "what") == "non-finite Ackermann control");
  const auto ins = b.Events("in.driving_command");
  CHECK(ins.size() == 1);
  if (!ins.empty()) CHECK(IsNull(ins[0], "acceleration"));
}

void TestEveryWorldSnapshotIsLogged() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 4.0));
  b.shell.OnSnapshot(Snapshot(9, 0.45, 9.0));
  b.shell.OnSnapshot(Snapshot(11, 0.55, 4.5));
  const auto snaps = b.Events("in.world_snapshot");
  CHECK(snaps.size() == 3);
  if (snaps.size() == 3) {
    CHECK(Flag(snaps[0], "kept") && !Flag(snaps[1], "kept") && Flag(snaps[2], "kept"));
    CHECK_EQ_D(Num(snaps[1], "frame"), 9.0);
    CHECK_EQ_D(Num(snaps[2], "t_sim_s"), 0.55);
    CHECK_EQ_D(Num(snaps[2], "speed_mps"), 4.5);
    CHECK(Flag(snaps[2], "egoPresent"));
  }
}

// A snapshot without the ego vehicle is logged, not kept, and reported once.
void TestASnapshotWithoutTheEgoVehicleIsNotKept() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 0.0, false));
  b.shell.OnSnapshot(Snapshot(11, 0.55, 0.0, false));
  b.shell.OnCommand(Command(1, 0.50), 1.0);
  CHECK(fake::CallCounts().apply == 0);
  const auto snaps = b.Events("in.world_snapshot");
  CHECK(snaps.size() == 2);
  if (!snaps.empty()) {
    CHECK(!Flag(snaps[0], "kept"));
    CHECK(IsNull(snaps[0], "speed_mps"));
  }
  CHECK(b.Events("error").size() == 1);
  const auto drops = b.Events("drop");
  CHECK(drops.size() == 1);
  if (!drops.empty()) {
    CHECK(Str(drops[0], "reason") == "delay");
    CHECK(IsNull(drops[0], "newestWorldTime_sim_s"));
  }
}

// The client's snapshot handler reaches the shell.
void TestAttachToSimulatorRegistersTheHandler() {
  Bench b;
  std::string error;
  CHECK(AttachToSimulator(&b.shell, &error));
  CHECK(fake::CallCounts().startSnapshots == 1);
  CHECK(fake::EmitSnapshot(Snapshot(5, 0.25, 3.0)));
  b.shell.OnCommand(Command(1, 0.25, 0.0F), 1.0);
  CHECK(fake::Applied().size() == 1);
  if (!fake::Applied().empty()) CHECK_EQ_D(fake::Applied().front().speed, 3.0F);
}

// The first command of a run carries 1. A first command with 2 is a loss, and
// counting resumes from it: a later 1 is a repetition, 3 is applied.
void TestTheFirstCommandOfARun() {
  Bench b;
  b.shell.OnSnapshot(Snapshot(10, 0.50, 0.0));
  b.shell.OnCommand(Command(2, 0.50), 1.0);
  CHECK(fake::Applied().empty());
  b.shell.OnCommand(Command(1, 0.50), 1.1);
  CHECK(fake::Applied().empty());
  b.shell.OnCommand(Command(3, 0.50, 1.0F), 1.2);
  CHECK(fake::Applied().size() == 1);
  if (!fake::Applied().empty()) CHECK_EQ_D(fake::Applied().front().speed, 2.0F);
  const auto drops = b.Events("drop");
  CHECK(drops.size() == 2);
  if (drops.size() == 2) {
    CHECK(Str(drops[0], "reason") == "loss");
    CHECK(Str(drops[1], "reason") == "repetition");
    CHECK_EQ_D(Num(drops[1], "referenceSeq"), 2.0);
  }
}

}  // namespace

int main() {
  TestAcceptedCommandIsAppliedAndLogged();
  TestEachRejectionIsLoggedAndNothingIsApplied();
  TestNothingIsAppliedAfterARejection();
  TestAfterALossTheNextCommandIsApplied();
  TestARefusedApplicationIsAnError();
  TestANonFiniteControlIsNotSent();
  TestEveryWorldSnapshotIsLogged();
  TestASnapshotWithoutTheEgoVehicleIsNotKept();
  TestAttachToSimulatorRegistersTheHandler();
  TestTheFirstCommandOfARun();
  return Finish("adapter_shell_test");
}
