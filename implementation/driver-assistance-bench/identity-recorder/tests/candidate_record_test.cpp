// Unit tests of the candidate record (candidate_record.h): the JSON, the event payload and the record writer. The
// record writer's tests write into a real temporary directory (TMPDIR).
#include <sys/stat.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>

#include "candidate_record.h"
#include "check.h"
#include "fake_file_system.h"
#include "file_system.h"
#include "record_inputs.h"
#include "sha256.h"

namespace id = de4sdv::driver_assistance::identity;
using de4sdv::driver_assistance::CandidateRecordEventPayload;

namespace {

const char* kRevision = "0123456789abcdef0123456789abcdef01234567";

id::RecordInputs SyntheticInputs() {
  id::test::FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  id::RecorderOptions o;
  o.run_dir = "/stage/run";
  id::RecordInputs in;
  std::string error;
  CHECK(id::ResolveInputs(o, fs, &in, &error));
  return in;
}

id::RecordStamp Stamp() {
  id::RecordStamp s;
  s.host = "score";
  s.record_path = "/stage/run/score/candidate_record.json";
  s.written_real_ns = 1763500000123456789LL;
  s.written_mono_ns = 987654321;
  return s;
}

bool Contains(const std::string& text, const std::string& part) { return text.find(part) != std::string::npos; }

void TestTheRecordHoldsEveryValueTheMappingNames() {
  const id::RecordInputs in = SyntheticInputs();
  const std::string json = id::RecordJson(in, "vision_pilot", Stamp());
  CHECK(Contains(json, "\"schema\":\"de4sdv.driver_assistance.candidate_record.v1\""));
  CHECK(Contains(json, "\"mapping\":\"MAP-DRIVING-DA-CANDIDATE-RECORD\""));
  CHECK(Contains(json, std::string("\"upstream_revision\":\"") + kRevision + "\""));
  CHECK(Contains(json, "\"source_difference\":{\"bytes\":" + std::to_string(id::DiffBytes(in)) + ","));
  CHECK(Contains(json, "\"text\":\"diff --git a/x b/x\\n+one\\n\""));  // verbatim, escaped
  CHECK(Contains(json, "\"role\":\"H.yaml\",\"path\":\"/stage/vision_pilot/config/H.yaml\",\"sha256\":\"" +
                           id::Sha256Hex("H: synthetic-h\n") + "\""));
  CHECK(Contains(json, "\"network_files\":[{\"role\":\"network autodrive\""));
  CHECK(Contains(json, "\"binaries\":[{"));
  CHECK(Contains(json, "\"link_target\":\"libonnxruntime.so.1\""));
  CHECK(Contains(json, "\"ldconfig_conf\":{\"path\":\"/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf\""));
  CHECK(Contains(json, "\"working_dir\":\"/stage/vision_pilot\""));
  CHECK(Contains(json, "\"launch_config_text\":\"{\\n  \\\"schema_version\\\": 2,"));
  CHECK(Contains(json, "\"written_real_ns\":1763500000123456789"));
  CHECK(json.back() == '\n');
  // deterministic
  CHECK(json == id::RecordJson(SyntheticInputs(), "vision_pilot", Stamp()));
  // the difference: bytes and the digest of the files in name order
  CHECK(id::DiffBytes(in) == std::strlen("diff --git a/x b/x\n+one\n") + std::strlen("diff --git a/y b/y\n+two\n"));
  CHECK(id::DiffSha256(in) == id::Sha256Hex("diff --git a/x b/x\n+one\ndiff --git a/y b/y\n+two\n"));
}

void TestOneChangeGivesAnotherRecord() {
  id::test::FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  fs.Put("/stage/vision_pilot/config/H.yaml", "H: synthetic-h2\n");
  id::RecorderOptions o;
  o.run_dir = "/stage/run";
  id::RecordInputs changed;
  std::string error;
  CHECK(id::ResolveInputs(o, fs, &changed, &error));
  CHECK(id::RecordJson(changed, "vision_pilot", Stamp()) != id::RecordJson(SyntheticInputs(), "vision_pilot", Stamp()));
}

void TestThePayload() {
  CandidateRecordEventPayload p{};
  std::string error;
  const std::string sha = id::Sha256Hex("record");
  CHECK(id::MakeEventPayload(sha, kRevision, 42, "/stage/run/score/candidate_record.json", &p, &error));
  CHECK(std::string(p.recordSha256) == sha);
  CHECK(std::string(p.upstreamRevision) == kRevision);
  CHECK(p.diffBytes == 42u);
  CHECK(std::string(p.recordPath) == "/stage/run/score/candidate_record.json");
  CHECK(p.recordSha256[64] == '\0' && p.upstreamRevision[40] == '\0');
  CHECK(!id::MakeEventPayload(sha, kRevision, 0, "/x", &p, &error));  // never empty
  CHECK(!id::MakeEventPayload(sha, kRevision, 0x100000000ull, "/x", &p, &error));
  CHECK(!id::MakeEventPayload(sha.substr(1), kRevision, 1, "/x", &p, &error));
  CHECK(!id::MakeEventPayload(sha, "014e0e7a", 1, "/x", &p, &error));
  CHECK(!id::MakeEventPayload(sha, kRevision, 1, "", &p, &error));
  CHECK(!id::MakeEventPayload(sha, kRevision, 1, std::string(256, 'p'), &p, &error));
  CHECK(id::MakeEventPayload(sha, kRevision, 1, std::string(255, 'p'), &p, &error));
  CHECK(p.recordPath[255] == '\0');
}

std::string Slurp(const std::string& path) {
  id::PosixFileSystem fs;
  std::string out;
  fs.ReadFile(path, &out);
  return out;
}

void TestTheRecordWriter() {
  const char* tmp = std::getenv("TMPDIR");
  const std::filesystem::path base =
      std::filesystem::path(tmp != nullptr ? tmp : "/tmp") / ("record_writer_test_" + std::to_string(::getpid()));
  std::filesystem::remove_all(base);
  const std::string path = (base / "run" / "score" / "candidate_record.json").string();
  std::string error;
  CHECK(id::WriteRecordFile(path, "{\"a\":1}\n", &error));  // creates the directories
  CHECK(Slurp(path) == "{\"a\":1}\n");
  CHECK(id::WriteRecordFile(path, "{\"b\":2}\n", &error));  // replaces
  CHECK(Slurp(path) == "{\"b\":2}\n");
  int entries = 0;
  for (const auto& e : std::filesystem::directory_iterator(base / "run" / "score")) {
    ++entries;
    CHECK(e.path().filename() == "candidate_record.json");  // no temporary left
  }
  CHECK(entries == 1);
  id::PosixFileSystem fs;
  std::string sha;
  std::uint64_t size = 0;
  CHECK(fs.HashFile(path, &sha, &size) && sha == id::Sha256Hex("{\"b\":2}\n") && size == 8u);
  // a directory where a file of the path should be
  const std::string blocked = (base / "run" / "score" / "candidate_record.json" / "x.json").string();
  CHECK(!id::WriteRecordFile(blocked, "x", &error));
  CHECK(!error.empty());
  // an unwritable directory (skipped as root, who may write anywhere)
  if (::geteuid() != 0) {
    const std::filesystem::path ro = base / "ro";
    std::filesystem::create_directories(ro);
    ::chmod(ro.c_str(), 0555);
    CHECK(!id::WriteRecordFile((ro / "r.json").string(), "x", &error));
    ::chmod(ro.c_str(), 0755);
  }
  std::filesystem::remove_all(base);
}

void TestPathHelpers() {
  CHECK(id::JoinPath("/a", "b") == "/a/b");
  CHECK(id::JoinPath("/a/", "b") == "/a/b");
  CHECK(id::JoinPath("/a", "/b") == "/b");
  CHECK(id::ParentPath("/tmp/de4sdv-da-bench/run") == "/tmp/de4sdv-da-bench");
  CHECK(id::ParentPath("/tmp/de4sdv-da-bench/run/") == "/tmp/de4sdv-da-bench");
  CHECK(id::ParentPath("/run") == "/");
  CHECK(id::ParentPath("run") == ".");
}

}  // namespace

int main() {
  TestTheRecordHoldsEveryValueTheMappingNames();
  TestOneChangeGivesAnotherRecord();
  TestThePayload();
  TestTheRecordWriter();
  TestPathHelpers();
  return de4sdv::driver_assistance::actuation::test::Finish("candidate_record_test");
}
