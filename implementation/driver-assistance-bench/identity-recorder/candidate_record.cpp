// The candidate record (candidate_record.h). C++17 and POSIX.
#include "candidate_record.h"

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <string>
#include <system_error>

#include <fcntl.h>
#include <unistd.h>

#include "run_log.h"
#include "sha256.h"

namespace de4sdv::driver_assistance::identity {

namespace {

using ::de4sdv::driver_assistance::JsonString;

std::string Files(const std::vector<HashedFile>& files) {
  std::string out = "[";
  for (std::size_t i = 0; i < files.size(); ++i) {
    const HashedFile& f = files[i];
    if (i != 0) out += ",";
    out += "{\"role\":" + JsonString(f.role) + ",\"path\":" + JsonString(f.path) +
           ",\"sha256\":" + JsonString(f.sha256) + ",\"bytes\":" + std::to_string(f.bytes);
    if (!f.link_target.empty()) out += ",\"link_target\":" + JsonString(f.link_target);
    out += "}";
  }
  return out + "]";
}

std::string Strings(const std::vector<std::string>& items) {
  std::string out = "[";
  for (std::size_t i = 0; i < items.size(); ++i) {
    if (i != 0) out += ",";
    out += JsonString(items[i]);
  }
  return out + "]";
}

std::string Launch(const LaunchSettings& l) {
  std::string env = "{";
  for (std::size_t i = 0; i < l.environment.size(); ++i) {
    if (i != 0) env += ",";
    env += JsonString(l.environment[i].first) + ":" + JsonString(l.environment[i].second);
  }
  env += "}";
  return "{\"component\":" + JsonString(l.component) + ",\"application_type\":" + JsonString(l.application_type) +
         ",\"binary_path\":" + JsonString(l.binary_path) + ",\"working_dir\":" + JsonString(l.working_dir) +
         ",\"process_arguments\":" + Strings(l.process_arguments) + ",\"environment\":" + env +
         ",\"depends_on\":" + Strings(l.depends_on) + "}";
}

bool CopyInto(char* dst, std::size_t capacity, const std::string& value) {
  if (value.size() >= capacity) return false;
  std::memset(dst, 0, capacity);
  std::memcpy(dst, value.data(), value.size());
  return true;
}

}  // namespace

std::uint64_t DiffBytes(const RecordInputs& inputs) {
  std::uint64_t total = 0;
  for (const DiffFile& diff : inputs.diffs) total += diff.text.size();
  return total;
}

std::string DiffSha256(const RecordInputs& inputs) {
  Sha256 hash;
  for (const DiffFile& diff : inputs.diffs) hash.Update(diff.text);
  return hash.HexDigest();
}

std::string RecordJson(const RecordInputs& inputs, const std::string& candidate, const RecordStamp& stamp) {
  std::string diffs = "[";
  for (std::size_t i = 0; i < inputs.diffs.size(); ++i) {
    const DiffFile& d = inputs.diffs[i];
    if (i != 0) diffs += ",";
    diffs += "{\"name\":" + JsonString(d.name) + ",\"sha256\":" + JsonString(d.sha256) +
             ",\"bytes\":" + std::to_string(d.text.size()) + ",\"text\":" + JsonString(d.text) + "}";
  }
  diffs += "]";
  std::string launch = "[";
  for (std::size_t i = 0; i < inputs.launch.size(); ++i) {
    if (i != 0) launch += ",";
    launch += Launch(inputs.launch[i]);
  }
  launch += "]";
  std::string out = "{";
  out += "\"schema\":" + JsonString(kRecordSchema);
  out += ",\"mapping\":\"MAP-DRIVING-DA-CANDIDATE-RECORD\"";
  out += ",\"host\":" + JsonString(stamp.host);
  out += ",\"record_path\":" + JsonString(stamp.record_path);
  out += ",\"written_real_ns\":" + std::to_string(stamp.written_real_ns);
  out += ",\"written_mono_ns\":" + std::to_string(stamp.written_mono_ns);
  out += ",\"upstream_revision\":" + JsonString(inputs.upstream_revision);
  out += ",\"source_difference\":{\"bytes\":" + std::to_string(DiffBytes(inputs)) +
         ",\"sha256\":" + JsonString(DiffSha256(inputs)) + ",\"files\":" + diffs + "}";
  out += ",\"candidate\":{\"component\":" + JsonString(candidate) +
         ",\"source_mode\":" + JsonString(inputs.candidate_source_mode) +
         ",\"model_precision\":" + JsonString(inputs.candidate_precision) + "}";
  out += ",\"configuration_files\":" + Files(inputs.configuration);
  out += ",\"network_files\":" + Files(inputs.networks);
  out += ",\"binaries\":" + Files(inputs.binaries);
  out += ",\"runtime_libraries\":" + Files(inputs.runtime_libraries);
  out += ",\"ldconfig_conf\":{\"path\":" + JsonString(inputs.ldconfig_conf_path) +
         ",\"text\":" + JsonString(inputs.ldconfig_conf_text) + "}";
  out += ",\"launch_settings\":{\"launch_config_path\":" + JsonString(inputs.launch_config_path) +
         ",\"launch_config_text\":" + JsonString(inputs.launch_config_text) + ",\"components\":" + launch + "}";
  out += "}\n";
  return out;
}

bool MakeEventPayload(const std::string& record_sha256, const std::string& upstream_revision,
                      std::uint64_t diff_bytes, const std::string& record_path, CandidateRecordEventPayload* out,
                      std::string* error) {
  CandidateRecordEventPayload p{};
  if (!IsLowerHex(record_sha256, 64)) {
    *error = "the record digest is not 64 lowercase hex digits";
    return false;
  }
  if (!IsLowerHex(upstream_revision, 40)) {
    *error = "the upstream revision is not 40 lowercase hex digits";
    return false;
  }
  if (diff_bytes == 0 || diff_bytes > 0xFFFFFFFFull) {
    *error = "the source difference is empty or does not fit 32 bits";
    return false;
  }
  if (record_path.empty() || !CopyInto(p.recordPath, sizeof p.recordPath, record_path)) {
    *error = "the record path is empty or longer than 255 bytes";
    return false;
  }
  CopyInto(p.recordSha256, sizeof p.recordSha256, record_sha256);
  CopyInto(p.upstreamRevision, sizeof p.upstreamRevision, upstream_revision);
  p.diffBytes = static_cast<std::uint32_t>(diff_bytes);
  *out = p;
  return true;
}

bool WriteRecordFile(const std::string& path, const std::string& bytes, std::string* error) {
  const std::filesystem::path target(path);
  std::error_code ec;
  std::filesystem::create_directories(target.parent_path(), ec);
  if (ec) {
    *error = "cannot create " + target.parent_path().string() + ": " + ec.message();
    return false;
  }
  const std::string temporary = path + ".tmp." + std::to_string(static_cast<long long>(::getpid()));
  const int fd = ::open(temporary.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
  if (fd < 0) {
    *error = "cannot create " + temporary + ": " + std::strerror(errno);
    return false;
  }
  std::size_t written = 0;
  while (written < bytes.size()) {
    const ssize_t n = ::write(fd, bytes.data() + written, bytes.size() - written);
    if (n < 0) {
      if (errno == EINTR) continue;
      *error = "cannot write " + temporary + ": " + std::strerror(errno);
      ::close(fd);
      ::unlink(temporary.c_str());
      return false;
    }
    written += static_cast<std::size_t>(n);
  }
  if (::fsync(fd) != 0 || ::close(fd) != 0) {
    *error = "cannot flush " + temporary + ": " + std::strerror(errno);
    ::unlink(temporary.c_str());
    return false;
  }
  if (::rename(temporary.c_str(), path.c_str()) != 0) {
    *error = "cannot rename " + temporary + " to " + path + ": " + std::strerror(errno);
    ::unlink(temporary.c_str());
    return false;
  }
  return true;
}

}  // namespace de4sdv::driver_assistance::identity
