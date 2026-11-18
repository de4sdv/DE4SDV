// Tests of the actuation adapter's logic core (actuation_core.h) against the
// rules of MAP-DRIVING-DA-COMMAND's transformationRule (PSR) and the part def
// DrivingCommandActuationAdapter.
//
// Valid commands are built with DrivingCommandCheckValue from payloads.h, the
// ICD's check value, which interfaces/tests/payloads_test.cpp checks against
// zlib's crc32. tests/test_actuation_adapter_shell.py builds its commands
// with Python's zlib and struct instead, and computes its expected controls
// with Python's math, independently of this file.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

#include "actuation_core.h"
#include "check.h"

using de4sdv::driver_assistance::DrivingCommandCheckValue;
using de4sdv::driver_assistance::DrivingCommandEventPayload;
using de4sdv::driver_assistance::actuation::AckermannControl;
using de4sdv::driver_assistance::actuation::ActuationCore;
using de4sdv::driver_assistance::actuation::CommandDecision;
using de4sdv::driver_assistance::actuation::DropReason;
using de4sdv::driver_assistance::actuation::DropReasonName;
using de4sdv::driver_assistance::actuation::IssueTimeTooOld;
using de4sdv::driver_assistance::actuation::ToAckermannControl;
using de4sdv::driver_assistance::actuation::WorldSnapshot;
using de4sdv::driver_assistance::actuation::test::Finish;

namespace {

constexpr double kPi = 3.14159265358979323846;

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

WorldSnapshot World(std::uint64_t frame, double simTimeS, double speedMps = 0.0) {
  WorldSnapshot world;
  world.frame = frame;
  world.simTimeS = simTimeS;
  world.speedMps = speedMps;
  return world;
}

// A core that has seen one world snapshot at 10.0 s, 5 m/s.
ActuationCore CoreAt10s() {
  ActuationCore core;
  core.OnWorldSnapshot(World(200, 10.0, 5.0));
  return core;
}

bool Accepted(const CommandDecision& d) { return d.accepted && d.reason == DropReason::kNone; }
bool Rejected(const CommandDecision& d, DropReason reason) {
  return !d.accepted && d.reason == reason;
}

// ------------------------------------------------------------------ names

void TestDropReasonNames() {
  CHECK(std::strcmp(DropReasonName(DropReason::kNone), "none") == 0);
  CHECK(std::strcmp(DropReasonName(DropReason::kLoss), "loss") == 0);
  CHECK(std::strcmp(DropReasonName(DropReason::kRepetition), "repetition") == 0);
  CHECK(std::strcmp(DropReasonName(DropReason::kCorruption), "corruption") == 0);
  CHECK(std::strcmp(DropReasonName(DropReason::kDelay), "delay") == 0);
}

// ------------------------------------------------------------------ sequence

// The count runs "from 1 in each run": the first command carries 1.
void TestFirstCommandOfARunCarriesOne() {
  ActuationCore core = CoreAt10s();
  CHECK(core.LastAcceptedSequence() == 0);
  const CommandDecision first = core.OnCommand(Command(1, 10.0));
  CHECK(Accepted(first));
  CHECK(first.crcOk);
  CHECK(first.lastAcceptedSequence == 0);
  CHECK(core.LastAcceptedSequence() == 1);
}

void TestFirstCommandWithTwoIsALoss() {
  ActuationCore core = CoreAt10s();
  CHECK(Rejected(core.OnCommand(Command(2, 10.0)), DropReason::kLoss));
  CHECK(core.LastAcceptedSequence() == 0);
}

void TestFirstCommandWithZeroIsARepetition() {
  ActuationCore core = CoreAt10s();
  CHECK(Rejected(core.OnCommand(Command(0, 10.0)), DropReason::kRepetition));
  CHECK(core.LastAcceptedSequence() == 0);
}

void TestConsecutiveCommandsAreAccepted() {
  ActuationCore core = CoreAt10s();
  for (std::uint32_t n = 1; n <= 5; ++n) {
    CHECK(Accepted(core.OnCommand(Command(n, 10.0))));
    CHECK(core.LastAcceptedSequence() == n);
  }
}

// A repeat is rejected and leaves the chain intact: the next count is accepted.
void TestRepeatIsRejectedAndTheNextCountIsAccepted() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  CHECK(Accepted(core.OnCommand(Command(2, 10.0))));
  const CommandDecision repeat = core.OnCommand(Command(2, 10.0));
  CHECK(Rejected(repeat, DropReason::kRepetition));
  CHECK(repeat.crcOk);
  CHECK(repeat.lastAcceptedSequence == 2);
  CHECK(Rejected(core.OnCommand(Command(1, 10.0)), DropReason::kRepetition));
  CHECK(core.LastAcceptedSequence() == 2);
  CHECK(Accepted(core.OnCommand(Command(3, 10.0))));
}

// A gap against a repeat: the command that reveals the gap is a loss, not a
// repetition, and it is rejected.
void TestGapIsALossAndTheRevealingCommandIsRejected() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  CHECK(Accepted(core.OnCommand(Command(2, 10.0))));
  const CommandDecision gap = core.OnCommand(Command(4, 10.0));
  CHECK(Rejected(gap, DropReason::kLoss));
  CHECK(gap.crcOk);
  CHECK(gap.lastAcceptedSequence == 2);
  CHECK(core.LastAcceptedSequence() == 2);
}

// "Not one more than that of the last accepted": after a gap every later count
// is not last accepted + 1, so each is rejected as a loss, until the missing
// count itself arrives.
void TestAfterAGapLaterCountsStayRejected() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  CHECK(Rejected(core.OnCommand(Command(3, 10.0)), DropReason::kLoss));
  CHECK(Rejected(core.OnCommand(Command(4, 10.0)), DropReason::kLoss));
  CHECK(Rejected(core.OnCommand(Command(5, 10.0)), DropReason::kLoss));
  CHECK(Rejected(core.OnCommand(Command(3, 10.0)), DropReason::kLoss));
  CHECK(core.LastAcceptedSequence() == 1);
  CHECK(Accepted(core.OnCommand(Command(2, 10.0))));
  CHECK(Accepted(core.OnCommand(Command(3, 10.0))));
}

// A count far ahead of the last accepted one is a loss.
void TestAFarCountIsALoss() {
  ActuationCore core = CoreAt10s();
  CHECK(Rejected(core.OnCommand(Command(0xFFFFFFFFu, 10.0)), DropReason::kLoss));
}

// ------------------------------------------------------------------ corruption

void TestCorruptedFieldIsACorruption() {
  ActuationCore core = CoreAt10s();
  DrivingCommandEventPayload command = Command(1, 10.0, -2.0F, 3.0F);
  command.acceleration = -2.5F;  // changed after the check value was computed
  const CommandDecision decision = core.OnCommand(command);
  CHECK(Rejected(decision, DropReason::kCorruption));
  CHECK(!decision.crcOk);
  CHECK(core.LastAcceptedSequence() == 0);
}

void TestCorruptedCheckValueIsACorruption() {
  ActuationCore core = CoreAt10s();
  DrivingCommandEventPayload command = Command(1, 10.0);
  command.checkValue ^= 0x00010000u;
  CHECK(Rejected(core.OnCommand(command), DropReason::kCorruption));
}

// One bit of each field flipped in turn: every one is a corruption.
void TestEveryFieldIsCovered() {
  const DrivingCommandEventPayload good = Command(1, 10.0, 1.0F, -4.0F);
  for (std::size_t byte = 0; byte < sizeof good; ++byte) {
    DrivingCommandEventPayload bad = good;
    unsigned char raw[sizeof bad];
    std::memcpy(raw, &bad, sizeof bad);
    raw[byte] ^= 0x01;
    std::memcpy(&bad, raw, sizeof bad);
    ActuationCore core = CoreAt10s();
    CHECK(Rejected(core.OnCommand(bad), DropReason::kCorruption));
  }
}

// The check value is checked first: a corrupted count that would read as a
// repetition, or a corrupted command that is also delayed, is a corruption.
void TestCorruptionIsCheckedFirst() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  DrivingCommandEventPayload command = Command(2, 10.0);
  command.sequenceCount = 1;
  CHECK(Rejected(core.OnCommand(command), DropReason::kCorruption));
  DrivingCommandEventPayload old = Command(2, 9.0);
  old.checkValue ^= 1u;
  CHECK(Rejected(core.OnCommand(old), DropReason::kCorruption));
  CHECK(core.LastAcceptedSequence() == 1);
}

// After a corruption the corrupted count was never accepted: the next count
// is a loss (the same literal reading as after a gap).
void TestAfterACorruptionTheNextCountIsALoss() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  DrivingCommandEventPayload bad = Command(2, 10.0);
  bad.checkValue ^= 1u;
  CHECK(Rejected(core.OnCommand(bad), DropReason::kCorruption));
  CHECK(Rejected(core.OnCommand(Command(3, 10.0)), DropReason::kLoss));
}

// ------------------------------------------------------------------ delay

// Pairs whose difference of doubles exceeds 0.1 although the times are two
// 0.05 s steps apart; found with Python's float arithmetic, and checked below.
struct TimePair {
  double newest;
  double issue;
};
constexpr TimePair kExactlyOneTenth[] = {
    {12.55, 12.45},  // 0.10000000000000142
    {12.05, 11.95},  // 0.10000000000000142
    {0.4, 0.3},      // 0.10000000000000003
    {1.05, 0.95},    // 0.10000000000000009
};

void TestBoundaryPairsReallyMissOneTenth() {
  for (const TimePair& pair : kExactlyOneTenth) {
    CHECK(pair.newest - pair.issue > 0.1);
  }
  // 12.45 - 12.35 falls below 0.1 instead (0.09999999999999964).
  CHECK(12.45 - 12.35 < 0.1);
}

void TestExactlyOneTenthIsNotADelay() {
  for (const TimePair& pair : kExactlyOneTenth) {
    CHECK(!IssueTimeTooOld(pair.issue, pair.newest));
  }
  CHECK(!IssueTimeTooOld(12.35, 12.45));
}

// Times as a simulator that adds its 0.05 s step on every tick holds them.
void TestExactlyOneTenthOfAccumulatedStepsIsNotADelay() {
  double steps[601];
  steps[0] = 0.0;
  for (int k = 1; k <= 600; ++k) steps[k] = steps[k - 1] + 0.05;
  int above = 0;
  for (int k = 3; k <= 600; ++k) {
    if (steps[k] - steps[k - 2] > 0.1) ++above;
    CHECK(!IssueTimeTooOld(steps[k - 2], steps[k]));  // two steps: 100 ms
    CHECK(IssueTimeTooOld(steps[k - 3], steps[k]));   // three steps: 150 ms
  }
  CHECK(above > 100);  // the pitfall is real for many of these pairs
}

void TestOlderThanOneTenthIsADelay() {
  CHECK(IssueTimeTooOld(12.30, 12.45));  // 150 ms
  CHECK(IssueTimeTooOld(12.349, 12.45));  // 101 ms
  CHECK(!IssueTimeTooOld(12.351, 12.45));  // 99 ms
  CHECK(!IssueTimeTooOld(12.45, 12.45));
  // An issue time newer than the newest world time is not older, however far
  // ahead: the model rejects only an older one (the adapter's client may see
  // the snapshot after the candidate saw its image).
  CHECK(!IssueTimeTooOld(12.50, 12.45));
  CHECK(!IssueTimeTooOld(12.60, 12.45));
  CHECK(!IssueTimeTooOld(20.0, 12.45));
}

void TestNonFiniteTimeIsADelay() {
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const double inf = std::numeric_limits<double>::infinity();
  CHECK(IssueTimeTooOld(nan, 12.45));
  CHECK(IssueTimeTooOld(12.45, nan));
  CHECK(IssueTimeTooOld(-inf, 12.45));
  CHECK(IssueTimeTooOld(inf, 12.45));
}

void TestDelayedCommandIsRejected() {
  ActuationCore core;
  core.OnWorldSnapshot(World(249, 12.45, 5.0));
  CHECK(Accepted(core.OnCommand(Command(1, 12.35))));
  const CommandDecision late = core.OnCommand(Command(2, 12.30));
  CHECK(Rejected(late, DropReason::kDelay));
  CHECK(late.crcOk);
  CHECK(late.worldKnown);
  CHECK_EQ_D(late.world.simTimeS, 12.45);
  CHECK(core.LastAcceptedSequence() == 1);
}

void TestBoundaryCommandIsAccepted() {
  ActuationCore core;
  core.OnWorldSnapshot(World(251, 12.55, 5.0));
  CHECK(Accepted(core.OnCommand(Command(1, 12.45))));
}

// The delay is checked against the newest world time, which advances.
void TestTheNewestWorldTimeIsUsed() {
  ActuationCore core;
  core.OnWorldSnapshot(World(249, 12.45, 5.0));
  core.OnWorldSnapshot(World(250, 12.50, 5.0));
  CHECK(Rejected(core.OnCommand(Command(1, 12.35)), DropReason::kDelay));
}

void TestWithoutAWorldSnapshotACommandIsADelay() {
  ActuationCore core;
  const CommandDecision decision = core.OnCommand(Command(1, 0.0));
  CHECK(Rejected(decision, DropReason::kDelay));
  CHECK(!decision.worldKnown);
  CHECK(decision.crcOk);
}

// A gapped and delayed command is a loss: the sequence is checked before the time.
void TestSequenceIsCheckedBeforeTheTime() {
  ActuationCore core = CoreAt10s();
  CHECK(Rejected(core.OnCommand(Command(2, 9.0)), DropReason::kLoss));
}

// After a delay the delayed count was never accepted: the next count is a loss.
void TestAfterADelayTheNextCountIsALoss() {
  ActuationCore core = CoreAt10s();
  CHECK(Accepted(core.OnCommand(Command(1, 10.0))));
  CHECK(Rejected(core.OnCommand(Command(2, 9.85)), DropReason::kDelay));
  CHECK(Rejected(core.OnCommand(Command(3, 10.0)), DropReason::kLoss));
}

// ------------------------------------------------------------------ world snapshots

void TestOlderOrRepeatedFramesAreIgnored() {
  ActuationCore core;
  CHECK(!core.HasWorld());
  core.OnWorldSnapshot(World(10, 0.50, 3.0));
  CHECK(core.HasWorld());
  core.OnWorldSnapshot(World(9, 0.45, 9.0));
  CHECK(core.NewestWorld().frame == 10);
  CHECK_EQ_D(core.NewestWorld().speedMps, 3.0);
  core.OnWorldSnapshot(World(10, 0.50, 8.0));
  CHECK_EQ_D(core.NewestWorld().speedMps, 3.0);
  core.OnWorldSnapshot(World(11, 0.55, 4.0));
  CHECK(core.NewestWorld().frame == 11);
  CHECK_EQ_D(core.NewestWorld().speedMps, 4.0);
}

// ------------------------------------------------------------------ control

void TestControlFieldsOfAnAcceptedCommand() {
  ActuationCore core = CoreAt10s();  // v = 5 m/s
  const CommandDecision decision = core.OnCommand(Command(1, 10.0, -1.5F, 0.0F));
  CHECK(Accepted(decision));
  CHECK(decision.controlFinite);
  CHECK_EQ_D(decision.control.speed, 2.0);  // 5 + 2 * -1.5
  CHECK_EQ_D(decision.control.acceleration, -1.5);
  CHECK_EQ_D(decision.control.jerk, 10.0);
  CHECK_EQ_D(decision.control.steerSpeed, 0.0);
  CHECK_EQ_D(decision.control.steer, 0.0);
}

// speed = max(0, v + 2 * acceleration), v from the newest snapshot.
void TestSpeedRuleVectors() {
  struct Vector {
    double v;
    float acceleration;
    double speed;
  };
  const Vector vectors[] = {
      {0.0, 0.0F, 0.0},    {5.0, 0.0F, 5.0},     {5.0, 1.5F, 8.0},   {10.0, -2.5F, 5.0},
      {5.0, -2.5F, 0.0},   {5.0, -3.0F, 0.0},    {0.0, -5.0F, 0.0},  {16.5, -5.0F, 6.5},
      {1.0, -0.25F, 0.5},  {0.0, 1.0F, 2.0},
  };
  for (const Vector& vector : vectors) {
    DrivingCommandEventPayload command = Command(1, 0.0, vector.acceleration, 0.0F);
    const AckermannControl control = ToAckermannControl(command, vector.v);
    CHECK_EQ_D(control.speed, vector.speed);
    CHECK_EQ_D(control.acceleration, static_cast<double>(vector.acceleration));
    CHECK(control.speed >= 0.0);
  }
}

// Through the core: the speed comes from the newest snapshot.
void TestSpeedComesFromTheNewestSnapshot() {
  ActuationCore core;
  core.OnWorldSnapshot(World(1, 0.05, 4.0));
  core.OnWorldSnapshot(World(2, 0.10, 6.0));
  core.OnWorldSnapshot(World(1, 0.05, 1.0));  // older, ignored
  const CommandDecision decision = core.OnCommand(Command(1, 0.10, 0.5F));
  CHECK_EQ_D(decision.control.speed, 7.0);
}

// steer = -steeringAngle * pi / 180: the command's angle is positive to the
// left, CARLA's steer positive to the right.
void TestSteeringSignVectors() {
  struct Vector {
    float steeringAngle;
    double steer;
  };
  const Vector vectors[] = {
      {0.0F, 0.0},
      {10.0F, -10.0 * kPi / 180.0},
      {-10.0F, 10.0 * kPi / 180.0},
      {90.0F, -kPi / 2.0},
      {-1.0F, kPi / 180.0},
  };
  for (const Vector& vector : vectors) {
    const AckermannControl control =
        ToAckermannControl(Command(1, 0.0, 0.0F, vector.steeringAngle), 3.0);
    CHECK_NEAR(control.steer, vector.steer, 1e-15);
  }
  // A left command (positive angle) gives a negative steer, a right one positive.
  CHECK(ToAckermannControl(Command(1, 0.0, 0.0F, 5.0F), 3.0).steer < 0.0);
  CHECK(ToAckermannControl(Command(1, 0.0, 0.0F, -5.0F), 3.0).steer > 0.0);
}

void TestNonFiniteValuesGiveANonFiniteControl() {
  const float nan = std::numeric_limits<float>::quiet_NaN();
  ActuationCore core = CoreAt10s();
  const CommandDecision a = core.OnCommand(Command(1, 10.0, nan, 0.0F));
  CHECK(a.accepted);
  CHECK(!a.controlFinite);
  const CommandDecision s = core.OnCommand(Command(2, 10.0, 0.0F, nan));
  CHECK(s.accepted);
  CHECK(!s.controlFinite);
  const CommandDecision ok = core.OnCommand(Command(3, 10.0, 0.0F, 0.0F));
  CHECK(ok.accepted);
  CHECK(ok.controlFinite);
}

void TestARejectedDecisionCarriesNoControl() {
  ActuationCore core = CoreAt10s();
  const CommandDecision decision = core.OnCommand(Command(2, 10.0, 1.0F, 5.0F));
  CHECK(!decision.accepted);
  CHECK_EQ_D(decision.control.speed, 0.0);
  CHECK_EQ_D(decision.control.steer, 0.0);
  CHECK_EQ_D(decision.control.acceleration, 0.0);
  CHECK_EQ_D(decision.control.jerk, 0.0);
}

}  // namespace

int main() {
  TestDropReasonNames();
  TestFirstCommandOfARunCarriesOne();
  TestFirstCommandWithTwoIsALoss();
  TestFirstCommandWithZeroIsARepetition();
  TestConsecutiveCommandsAreAccepted();
  TestRepeatIsRejectedAndTheNextCountIsAccepted();
  TestGapIsALossAndTheRevealingCommandIsRejected();
  TestAfterAGapLaterCountsStayRejected();
  TestAFarCountIsALoss();
  TestCorruptedFieldIsACorruption();
  TestCorruptedCheckValueIsACorruption();
  TestEveryFieldIsCovered();
  TestCorruptionIsCheckedFirst();
  TestAfterACorruptionTheNextCountIsALoss();
  TestBoundaryPairsReallyMissOneTenth();
  TestExactlyOneTenthIsNotADelay();
  TestExactlyOneTenthOfAccumulatedStepsIsNotADelay();
  TestOlderThanOneTenthIsADelay();
  TestNonFiniteTimeIsADelay();
  TestDelayedCommandIsRejected();
  TestBoundaryCommandIsAccepted();
  TestTheNewestWorldTimeIsUsed();
  TestWithoutAWorldSnapshotACommandIsADelay();
  TestSequenceIsCheckedBeforeTheTime();
  TestAfterADelayTheNextCountIsALoss();
  TestOlderOrRepeatedFramesAreIgnored();
  TestControlFieldsOfAnAcceptedCommand();
  TestSpeedRuleVectors();
  TestSpeedComesFromTheNewestSnapshot();
  TestSteeringSignVectors();
  TestNonFiniteValuesGiveANonFiniteControl();
  TestARejectedDecisionCarriesNoControl();
  return Finish("actuation_core_test");
}
