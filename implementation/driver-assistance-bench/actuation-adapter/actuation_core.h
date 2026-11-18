// DE4SDV driver-assistance bench (INC-DRIVING-002): the actuation adapter's
// logic core. Pure C++17: no simulator, middleware or clock.
//
// The model is the authority:
// textual-notation-of-model/packages/features/driving/
// driver_assistance_physical_software_realization.sysml ("PSR"), the part def
// DrivingCommandActuationAdapter and the transformationRule of the signal
// mapping MAP-DRIVING-DA-COMMAND. The wire form of the command is
// DrivingCommandEventPayload of interfaces/include/de4sdv/driver_assistance/
// payloads.h, with its check value DrivingCommandCheckValue (ICD.md).
//
// The shell (adapter_shell.h) feeds the core two inputs and applies what it
// returns:
//
//   OnWorldSnapshot()  the simulator client's newest world snapshot: frame,
//                      simulation time and the ego vehicle's speed (PSR
//                      simulationClockIn, vehicleSpeedIn);
//   OnCommand()        a driving command from the mw::com event (PSR
//                      drivingCommandIn).
//
// Rules, each from MAP-DRIVING-DA-COMMAND's transformationRule:
//
//  * Rejection. "The adapter rejects a command whose sequence count is not one
//    more than that of the last accepted, whose check value fails or whose
//    issue time is older than the newest world time by more than 0.1 s of
//    simulation time, and applies nothing in its place". The last accepted
//    count starts at 0, since the count runs "from 1 in each run"
//    (dataTypeAndUnit), so the first command of a run has to carry 1.
//    The part def names the reasons: "(a loss or a repetition)", "(a
//    corruption)", "(a delay)". Here a count above last+1 is a loss and a
//    count at or below the last accepted one is a repetition.
//    Read literally, "the last accepted" stays where it was after a
//    rejection, so the command that reveals a gap is rejected, and so is every
//    later one whose count is not last accepted + 1: after a loss, or after any
//    rejection, the run applies no further command unless the lost count
//    itself still arrives. This is the stricter of the readings and the one
//    implemented; README.md flags it.
//    Order of the checks: the check value first, since a corrupted command's
//    sequence count and issue time cannot be trusted; then the sequence count;
//    then the issue time. One reason per rejection.
//  * Delay. The issue time and the newest world time are simulation seconds
//    on one clock (PSR part def). They are compared in whole milliseconds,
//    each rounded to the nearest one: the bench's 0.05 s step makes every
//    simulation time a whole number of milliseconds (ICD.md), and a
//    difference of doubles does not hit 0.1 s exactly (12.45 - 12.35 is
//    0.10000000000000142). A command exactly 100 ms older is not "more than
//    0.1 s" older and passes. Without a world snapshot, or with a time that is
//    not finite, the age cannot be shown to be within 0.1 s: the command is
//    rejected as a delay (the stricter reading; the model does not say).
//  * Control. An accepted command becomes the simulator's Ackermann control:
//    steer = -steeringAngle * pi / 180 in rad; speed = max(0, v + 2 *
//    acceleration) with v the ego vehicle's speed in the newest world
//    snapshot; acceleration unchanged; jerk = 10.0; steerSpeed stays 0.0.
//    No PI loop, no watchdog and no stop response (PSR part def: "It has no
//    stop response of its own"); the autopilot is never set.
#pragma once

#include <cstdint>

#include "de4sdv/driver_assistance/payloads.h"

namespace de4sdv::driver_assistance::actuation {

// The constants of MAP-DRIVING-DA-COMMAND's transformationRule.
inline constexpr double kMaxCommandAgeMs = 100.0;  // "more than 0.1 s of simulation time"
inline constexpr double kSpeedHorizonS = 2.0;      // "speed = max(0, v + 2 * acceleration)"
inline constexpr double kJerk = 10.0;              // "jerk = 10.0"
inline constexpr double kSteerSpeed = 0.0;         // "steerSpeed stays at its default of 0.0"
inline constexpr double kPi = 3.14159265358979323846;

// One world snapshot as the simulator client reads it.
struct WorldSnapshot {
  std::uint64_t frame = 0;
  double simTimeS = 0.0;  // the snapshot's simulation time, seconds
  double speedMps = 0.0;  // the ego vehicle's speed in this snapshot, m/s
};

// PSR item def SimulatorAckermannControl: the five fields of CARLA's
// VehicleAckermannControl, in the model's names.
struct AckermannControl {
  double steer = 0.0;         // rad, positive to the right
  double steerSpeed = 0.0;    // rad/s
  double speed = 0.0;         // m/s
  double acceleration = 0.0;  // m/s^2
  double jerk = 0.0;          // m/s^3
};

enum class DropReason : std::uint8_t {
  kNone = 0,
  kLoss = 1,
  kRepetition = 2,
  kCorruption = 3,
  kDelay = 4,
};
// "none", "loss", "repetition", "corruption", "delay".
const char* DropReasonName(DropReason reason);

struct CommandDecision {
  bool accepted = false;
  DropReason reason = DropReason::kNone;
  bool crcOk = false;
  bool worldKnown = false;
  WorldSnapshot world;                     // the newest snapshot at the decision
  std::uint32_t lastAcceptedSequence = 0;  // before this command
  AckermannControl control;                // set when accepted
  // All five fields of control are finite. The model has no rule for a
  // command whose values give a non-finite control; the shell does not send
  // one to the simulator and logs an error (README.md, open question).
  bool controlFinite = false;
};

// MAP-DRIVING-DA-COMMAND's rule from an accepted command to the Ackermann
// control, with v the ego vehicle's speed in the newest world snapshot.
AckermannControl ToAckermannControl(const DrivingCommandEventPayload& command, double speedMps);

// True when the issue time is older than the newest world time by more than
// 0.1 s, compared in whole milliseconds, or when either time is not finite.
bool IssueTimeTooOld(double issueTimeS, double newestWorldTimeS);

// Not thread-safe: the shell serializes the two calls.
class ActuationCore {
 public:
  // Keeps the snapshot when it is the first or has a higher frame than the
  // one kept; an older or repeated frame changes nothing.
  void OnWorldSnapshot(const WorldSnapshot& snapshot);

  CommandDecision OnCommand(const DrivingCommandEventPayload& command);

  std::uint32_t LastAcceptedSequence() const { return last_accepted_; }
  bool HasWorld() const { return has_world_; }
  const WorldSnapshot& NewestWorld() const { return world_; }

 private:
  bool has_world_ = false;
  WorldSnapshot world_;
  std::uint32_t last_accepted_ = 0;
};

}  // namespace de4sdv::driver_assistance::actuation
