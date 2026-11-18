// DE4SDV driver-assistance bench (INC-DRIVING-002): what the identity recorder hashes, and where it finds it.
//
// MAP-DRIVING-DA-CANDIDATE-RECORD (PSR CandidateIdentityRecordingApplication) names the upstream revision, the
// source difference, the SHA-256 of each configuration, calibration, manifest and network file that the
// candidate's process reads (vision_pilot.conf, H.yaml, the DE4SDV interface configuration, the mw::com manifest and
// the network files) and the launch settings verbatim, the working directory included. The lead's answers of
// 2026-11-18 add homography_C_matrix.yaml, the binaries, the ldconfig conf of the GPU runtime and every library it
// names. ResolveInputs() finds all of them from the Launch Manager configuration, the way the processes will find
// them:
//
//   - the launch settings of every component: bin_dir/binary_name, working_dir, process_arguments and
//     environmental_variables, the component's deployment_config over the defaults (lifecycle_config.py merges
//     them so at v0.10.0, per the B6 README);
//   - the candidate's files by upstream's own lookup at the pin: find_config() takes config/<name> in the working
//     directory, else /usr/share/visionpilot/config/<name> (VisionPilot/modules/common/src/utils.cpp:3-12); the
//     networks are modules/models/weights/<net>_<precision>.onnx, else under /usr/share/visionpilot
//     (modules/models/src/inference.cpp:72-73,102-104), precision from model.precision of vision_pilot.conf;
//   - the interface configuration from DE4SDV_SCORE_INTERFACE_CONFIG, else config/de4sdv_score_interface.conf in the
//     working directory (score-interface settings.hpp), and the candidate's mw::com manifest from its mw_com.config;
//   - every file that a component's process argument or environment variable names (the other mw::com manifests,
//     the gateway configuration, the vsomeip configuration, the adapter's configuration);
//   - every file in each directory of the candidate's LD_LIBRARY_PATH (the ONNX Runtime libraries);
//   - the ldconfig conf and every shared library in each directory it lists (CUDA and cuDNN);
//   - the source difference: every *.diff of the facts directory, checked against its SHA256SUMS when present;
//   - the upstream revision from facts/upstream_revision.txt, unless given.
//
// A file the candidate reads that is missing is an error: no record, so the Launch Manager never sees the
// recorder report running and never starts the candidate (REQ-DRIVING-044).
#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "file_system.h"

namespace de4sdv::driver_assistance::identity {

struct RecorderOptions {
  std::string run_dir;            // --run-dir, required
  std::string stage_root;         // default: the parent of run_dir
  std::string launch_config;      // default: <stage_root>/config/launch_manager_config.json
  std::string candidate = "vision_pilot";  // the candidate's component name in the Launch Manager configuration
  std::string ldconfig_conf;      // default: the one /etc/ld.so.conf.d/de4sdv-cuda-*.conf
  std::string ldconfig_dir = "/etc/ld.so.conf.d";
  std::string facts_dir;          // default: <stage_root>/facts
  std::string upstream_revision;  // default: <facts_dir>/upstream_revision.txt
  std::string system_root = "/usr/share/visionpilot";  // upstream's fallback root (utils.cpp:6)
  std::string host_name = "score";
};

// Fills the defaults that depend on other options.
void ApplyDefaults(RecorderOptions* options);

struct HashedFile {
  std::string role;     // what it is to the process, e.g. "vision_pilot.conf" or "process argument of gatewayd"
  std::string path;     // as the process finds it
  std::string sha256;   // hex
  std::uint64_t bytes = 0;
  std::string link_target;  // when path is a symbolic link
};

struct LaunchSettings {
  std::string component;
  std::string binary_path;
  std::string working_dir;
  std::vector<std::string> process_arguments;
  std::vector<std::pair<std::string, std::string>> environment;  // in the file's order
  std::string application_type;
  std::vector<std::string> depends_on;
};

struct DiffFile {
  std::string name;
  std::string sha256;
  std::string text;  // verbatim
};

struct RecordInputs {
  std::string upstream_revision;
  std::vector<DiffFile> diffs;          // in name order
  std::vector<HashedFile> configuration;  // configuration, calibration and manifest files
  std::vector<HashedFile> networks;       // the ONNX files
  std::vector<HashedFile> binaries;
  std::vector<HashedFile> runtime_libraries;  // LD_LIBRARY_PATH and the ldconfig conf's directories
  std::string ldconfig_conf_path;
  std::string ldconfig_conf_text;
  std::string launch_config_path;
  std::string launch_config_text;  // verbatim
  std::vector<LaunchSettings> launch;  // every component, in the file's order
  std::string candidate_source_mode;   // source.mode of vision_pilot.conf, as written
  std::string candidate_precision;     // model.precision
};

// The key = value lines of an upstream-style .conf: '#' starts a comment, a trailing ';' is dropped, blanks trimmed.
std::map<std::string, std::string> ParseConf(const std::string& text);

// The directories an ldconfig conf lists: absolute paths, one per line; comments and "include" lines are skipped.
std::vector<std::string> LdconfigDirectories(const std::string& text);

bool ResolveInputs(const RecorderOptions& options, const FileSystem& fs, RecordInputs* inputs, std::string* error);

}  // namespace de4sdv::driver_assistance::identity
