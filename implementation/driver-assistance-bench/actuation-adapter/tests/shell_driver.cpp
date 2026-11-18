// A driver for tests/test_actuation_adapter_shell.py: the shell with the fake
// simulator client, fed from a script on stdin, logging with RunLog to the
// file given as argv[1]. Script lines:
//
//   world <frame> <t_sim_s> <speed_mps>     a world snapshot with the ego vehicle
//   noego <frame> <t_sim_s>                 a world snapshot without it
//   cmd <48 hex digits>                     the 24 bytes of a DrivingCommandEventPayload
//
// The snapshots go through the handler AttachToSimulator registers. Every
// control the fake client receives is printed to stdout as one JSON line, with
// all digits, so the test compares what the simulator got with the records.
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

#include "adapter_shell.h"
#include "fake_simulator_client.h"
#include "run_log.h"

using de4sdv::driver_assistance::DrivingCommandEventPayload;
using de4sdv::driver_assistance::RunLog;
using de4sdv::driver_assistance::actuation::AdapterShell;
using de4sdv::driver_assistance::actuation::AttachToSimulator;
using de4sdv::driver_assistance::actuation::RecordWriter;
namespace sim = de4sdv::driver_assistance::actuation::simulator;
namespace fake = de4sdv::driver_assistance::actuation::simulator::fake;

namespace {

bool Hex(const std::string& text, unsigned char* out, std::size_t size) {
  if (text.size() != 2 * size) return false;
  for (std::size_t i = 0; i < size; ++i) {
    unsigned value = 0;
    if (std::sscanf(text.c_str() + 2 * i, "%2x", &value) != 1) return false;
    out[i] = static_cast<unsigned char>(value);
  }
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::fprintf(stderr, "usage: %s <log.jsonl> < script\n", argv[0]);
    return 2;
  }
  RunLog log(argv[1], "score", "actuationAdapter");
  if (!log.ok()) return 3;
  RecordWriter records(&log);
  AdapterShell shell(&records);
  std::string error;
  if (!AttachToSimulator(&shell, &error)) return 4;

  std::string line;
  std::size_t printed = 0;
  double arrival = 1000.0;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string kind;
    in >> kind;
    if (kind == "world" || kind == "noego") {
      sim::SnapshotSample sample;
      in >> sample.frame >> sample.simTimeS;
      sample.egoPresent = kind == "world";
      if (sample.egoPresent) in >> sample.speedMps;
      if (!in || !fake::EmitSnapshot(sample)) return 5;
    } else if (kind == "cmd") {
      std::string hex;
      in >> hex;
      unsigned char bytes[sizeof(DrivingCommandEventPayload)];
      if (!Hex(hex, bytes, sizeof bytes)) return 6;
      DrivingCommandEventPayload command;
      std::memcpy(&command, bytes, sizeof command);
      arrival += 0.001;
      shell.OnCommand(command, arrival);
    } else if (!kind.empty()) {
      return 7;
    }
    while (printed < fake::Applied().size()) {
      const sim::AppliedAckermannControl& c = fake::Applied()[printed++];
      std::printf("{\"steer\":%.17g,\"steerSpeed\":%.17g,\"speed\":%.17g,\"acceleration\":%.17g,"
                  "\"jerk\":%.17g}\n",
                  static_cast<double>(c.steer), static_cast<double>(c.steerSpeed),
                  static_cast<double>(c.speed), static_cast<double>(c.acceleration),
                  static_cast<double>(c.jerk));
    }
  }
  return 0;
}
