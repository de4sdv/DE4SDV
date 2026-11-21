// DE4SDV driver-assistance bench (INC-DRIVING-002): the check of a candidate record that a late subscriber got.
//
// The open readiness item (PSR phase8ScoreIntegrationPlaced): the record has to reach the vehicle interface, which
// subscribes after it was published. candidate_record_probe subscribes late on purpose and checks what it got
// with CheckReceivedRecord(): the event is well formed (the same rule as the vehicle interface's gate,
// score-interface core.cpp WellFormedCandidateRecord), the file at recordPath exists, its SHA-256 is recordSha256,
// and the file names the same revision and difference size as the event.
#pragma once

#include <string>

#include "de4sdv/driver_assistance/payloads.h"
#include "file_system.h"

namespace de4sdv::driver_assistance::identity {

struct ProbeVerdict {
  bool ok = false;
  std::string reason;  // empty when ok
  std::string record_sha256;
  std::string record_path;
};

ProbeVerdict CheckReceivedRecord(const CandidateRecordEventPayload& payload, const FileSystem& fs);

}  // namespace de4sdv::driver_assistance::identity
