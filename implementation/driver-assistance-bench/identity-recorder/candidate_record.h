// DE4SDV driver-assistance bench (INC-DRIVING-002): the candidate record of MAP-DRIVING-DA-CANDIDATE-RECORD.
//
// The record file (<run>/score/candidate_record.json, ICD.md) holds every value the mapping names: the upstream
// revision, the source difference verbatim, the SHA-256 of each configuration, calibration, manifest and network file,
// and the launch settings verbatim with the working directory; beside them the binaries and the runtime libraries
// (the lead's answers of 2026-11-18). Strings throughout, each SHA-256 in hex (the mapping's dataTypeAndUnit). The
// JSON field names are the bench's proposal: the model names the values, not a layout (README "Open points").
//
// The mw::com event (CandidateRecordEventPayload, payloads.h) carries the SHA-256 of the file's bytes, the revision,
// the size of the difference and the file's path.
#pragma once

#include <cstdint>
#include <string>

#include "de4sdv/driver_assistance/payloads.h"
#include "record_inputs.h"

namespace de4sdv::driver_assistance::identity {

inline constexpr const char* kRecordSchema = "de4sdv.driver_assistance.candidate_record.v1";
inline constexpr const char* kRecordFileName = "candidate_record.json";

struct RecordStamp {
  std::string host;
  std::string record_path;
  std::int64_t written_real_ns = 0;
  std::int64_t written_mono_ns = 0;
};

// The size of the source difference: the bytes of all its files.
std::uint64_t DiffBytes(const RecordInputs& inputs);

// The SHA-256 of the difference's files concatenated in name order.
std::string DiffSha256(const RecordInputs& inputs);

// The record file's bytes. Deterministic: the same inputs and stamp give the same bytes.
std::string RecordJson(const RecordInputs& inputs, const std::string& candidate, const RecordStamp& stamp);

// The event of the record. False, with the reason, when a value does not fit the payload: a revision that is not
// 40 hex digits, a digest that is not 64, an empty or oversized difference, a path of 256 bytes or more.
bool MakeEventPayload(const std::string& record_sha256, const std::string& upstream_revision,
                      std::uint64_t diff_bytes, const std::string& record_path, CandidateRecordEventPayload* out,
                      std::string* error);

// The record writer: writes bytes to path through a temporary file in the same directory, fsync, then rename, so
// a reader sees either no file or the whole record. Creates the directory. False, with the reason, on any error.
bool WriteRecordFile(const std::string& path, const std::string& bytes, std::string* error);

}  // namespace de4sdv::driver_assistance::identity
