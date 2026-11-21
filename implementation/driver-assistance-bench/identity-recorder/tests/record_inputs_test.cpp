// Unit tests of the identity recorder's input resolution (record_inputs.h), on the in-memory fake file system.
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#include "check.h"
#include "fake_file_system.h"
#include "record_inputs.h"
#include "sha256.h"

namespace id = de4sdv::driver_assistance::identity;
using id::test::FakeFileSystem;

namespace {

id::RecorderOptions Options() {
  id::RecorderOptions o;
  o.run_dir = "/stage/run";
  return o;
}

const id::HashedFile* FindRole(const std::vector<id::HashedFile>& files, const std::string& role) {
  for (const id::HashedFile& f : files) {
    if (f.role == role) return &f;
  }
  return nullptr;
}

const id::HashedFile* FindPath(const std::vector<id::HashedFile>& files, const std::string& path) {
  for (const id::HashedFile& f : files) {
    if (f.path == path) return &f;
  }
  return nullptr;
}

void TestDefaultsFollowTheRunDirectory() {
  id::RecorderOptions o = Options();
  id::ApplyDefaults(&o);
  CHECK(o.stage_root == "/stage");
  CHECK(o.launch_config == "/stage/config/launch_manager_config.json");
  CHECK(o.facts_dir == "/stage/facts");
}

void TestConfParsing() {
  const auto kv = id::ParseConf("# c\nspeed_limit      = 33.3;   # m/s\n a.b=c \nnoequals\nL = 2.860   # x\n");
  CHECK(kv.at("speed_limit") == "33.3");
  CHECK(kv.at("a.b") == "c");
  CHECK(kv.at("L") == "2.860");
  CHECK(kv.count("noequals") == 0);
}

void TestLdconfigDirectories() {
  const auto dirs = id::LdconfigDirectories("# c\n/a/lib\n\ninclude /etc/x/*.conf\nrelative\n  /b  # t\n");
  CHECK(dirs.size() == 2);
  CHECK(dirs.size() == 2 && dirs[0] == "/a/lib" && dirs[1] == "/b");
}

void TestTheSyntheticStageResolves() {
  FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  id::RecordInputs in;
  std::string error;
  CHECK(id::ResolveInputs(Options(), fs, &in, &error));
  CHECK(error.empty());
  CHECK(in.upstream_revision == "0123456789abcdef0123456789abcdef01234567");
  CHECK(in.diffs.size() == 2);
  CHECK(in.diffs.size() == 2 && in.diffs[0].name == "0001-a.diff" && in.diffs[1].name == "0002-b.diff");
  CHECK(in.candidate_source_mode == "score");
  CHECK(in.candidate_precision == "fp32");
  // the model's files first, in its order
  CHECK(in.configuration.size() >= 5);
  CHECK(in.configuration[0].role == "vision_pilot.conf");
  CHECK(in.configuration[0].path == "/stage/vision_pilot/config/vision_pilot.conf");
  CHECK(in.configuration[1].role == "H.yaml");
  CHECK(in.configuration[2].role == "homography_C_matrix.yaml");
  CHECK(in.configuration[3].role == "DE4SDV interface configuration");
  CHECK(in.configuration[4].role == "mw::com manifest of vision_pilot");
  CHECK(in.configuration[4].path == "/stage/config/mw_com_config_vision_pilot.json");
  CHECK(in.configuration[1].sha256 == id::Sha256Hex("H: synthetic-h\n"));
  CHECK(in.configuration[1].bytes == 15u);
  // every manifest and argument file of the other components
  CHECK(FindPath(in.configuration, "/stage/config/mw_com_config_identity_recorder.json") != nullptr);
  CHECK(FindPath(in.configuration, "/stage/config/mw_com_config_gatewayd.json") != nullptr);
  CHECK(FindPath(in.configuration, "/stage/config/gateway.bin") != nullptr);
  CHECK(FindRole(in.configuration, "Launch Manager configuration") != nullptr);
  CHECK(FindRole(in.configuration, "ldconfig conf of the GPU runtime") != nullptr);
  // no file twice
  for (std::size_t i = 0; i < in.configuration.size(); ++i) {
    for (std::size_t j = i + 1; j < in.configuration.size(); ++j) {
      CHECK(in.configuration[i].path != in.configuration[j].path);
    }
  }
  // the networks of the precision
  CHECK(in.networks.size() == 3);
  CHECK(FindPath(in.networks, "/stage/vision_pilot/modules/models/weights/autosteer_fp32.onnx") != nullptr);
  CHECK(FindPath(in.networks, "/stage/vision_pilot/modules/models/weights/autosteer_int8.onnx") == nullptr);
  // every binary
  CHECK(in.binaries.size() == 3);
  CHECK(FindPath(in.binaries, "/stage/bin/vision_pilot") != nullptr);
  // the libraries: LD_LIBRARY_PATH (link and target), then the ldconfig conf's directory (.so only, no dangling)
  CHECK(FindPath(in.runtime_libraries, "/stage/lib/libonnxruntime.so.1") != nullptr);
  const id::HashedFile* link = FindPath(in.runtime_libraries, "/stage/lib/libonnxruntime.so");
  CHECK(link != nullptr && link->link_target == "libonnxruntime.so.1" && link->sha256 == id::Sha256Hex("ort"));
  CHECK(FindPath(in.runtime_libraries, "/gpu/lib/libcudart.so.12") != nullptr);
  CHECK(FindPath(in.runtime_libraries, "/gpu/lib/libcudart.so.12.8.90") != nullptr);
  CHECK(FindPath(in.runtime_libraries, "/gpu/lib/libcudnn.so.9") != nullptr);
  CHECK(FindPath(in.runtime_libraries, "/gpu/lib/LICENSE") == nullptr);
  CHECK(FindPath(in.runtime_libraries, "/gpu/lib/libdangling.so") == nullptr);
  CHECK(in.ldconfig_conf_path == "/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf");
  CHECK(in.ldconfig_conf_text == "# synthetic\n/gpu/lib\n");
  // the launch settings, the component's values over the defaults
  CHECK(in.launch.size() == 3);
  const id::LaunchSettings* vp = nullptr;
  const id::LaunchSettings* gw = nullptr;
  for (const auto& l : in.launch) {
    if (l.component == "vision_pilot") vp = &l;
    if (l.component == "gatewayd") gw = &l;
  }
  CHECK(vp != nullptr && gw != nullptr);
  if (vp != nullptr && gw != nullptr) {
    CHECK(vp->working_dir == "/stage/vision_pilot");
    CHECK(gw->working_dir == "/stage");
    CHECK(vp->binary_path == "/stage/bin/vision_pilot");
    CHECK(vp->application_type == "Reporting_And_Supervised");
    CHECK(gw->application_type == "Native");
    CHECK(vp->depends_on.size() == 1 && vp->depends_on[0] == "identity_recorder");
    std::string shared;
    std::string ld;
    for (const auto& kv : vp->environment) {
      if (kv.first == "SHARED") shared = kv.second;
      if (kv.first == "LD_LIBRARY_PATH") ld = kv.second;
    }
    CHECK(shared == "own");
    CHECK(ld == "/stage/lib");
    CHECK(gw->process_arguments.size() == 4 && gw->process_arguments[0] == "-c");
  }
  CHECK(in.launch_config_text.find("\"schema_version\": 2") != std::string::npos);
}

void TestUpstreamsLookupPrefersTheWorkingDirectory() {
  FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  fs.Put("/usr/share/visionpilot/config/H.yaml", "system-h");
  fs.Remove("/stage/vision_pilot/config/homography_C_matrix.yaml");
  fs.Put("/usr/share/visionpilot/config/homography_C_matrix.yaml", "system-c");
  id::RecordInputs in;
  std::string error;
  CHECK(id::ResolveInputs(Options(), fs, &in, &error));
  CHECK(FindRole(in.configuration, "H.yaml") != nullptr &&
        FindRole(in.configuration, "H.yaml")->path == "/stage/vision_pilot/config/H.yaml");
  CHECK(FindRole(in.configuration, "homography_C_matrix.yaml") != nullptr &&
        FindRole(in.configuration, "homography_C_matrix.yaml")->path ==
            "/usr/share/visionpilot/config/homography_C_matrix.yaml");
}

void TestTheModelPrecisionSelectsTheNetworks() {
  FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  fs.Put("/stage/vision_pilot/config/vision_pilot.conf", "source.mode = score\nmodel.precision    = int8\n");
  id::RecordInputs in;
  std::string error;
  CHECK(id::ResolveInputs(Options(), fs, &in, &error));
  CHECK(FindPath(in.networks, "/stage/vision_pilot/modules/models/weights/autodrive_int8.onnx") != nullptr);
  CHECK(FindPath(in.networks, "/stage/vision_pilot/modules/models/weights/autodrive_fp32.onnx") == nullptr);
}

void ExpectFailure(FakeFileSystem* fs, const id::RecorderOptions& options, const std::string& fragment,
                   const char* what) {
  id::RecordInputs in;
  std::string error;
  const bool ok = id::ResolveInputs(options, *fs, &in, &error);
  CHECK(!ok);
  const bool named = error.find(fragment) != std::string::npos;
  CHECK(named);
  if (ok || !named) std::printf("  case %s: error was '%s'\n", what, error.c_str());
}

void TestEveryMissingInputIsAnError() {
  struct Case {
    const char* what;
    const char* remove;
    const char* fragment;
  };
  const Case cases[] = {
      {"conf", "/stage/vision_pilot/config/vision_pilot.conf", "vision_pilot.conf"},
      {"H", "/stage/vision_pilot/config/H.yaml", "H.yaml"},
      {"C", "/stage/vision_pilot/config/homography_C_matrix.yaml", "homography_C_matrix.yaml"},
      {"interface", "/stage/config/de4sdv_score_interface.conf", "DE4SDV interface configuration"},
      {"manifest", "/stage/config/mw_com_config_vision_pilot.json", "mw::com manifest of vision_pilot"},
      {"network", "/stage/vision_pilot/modules/models/weights/autospeed_fp32.onnx", "autospeed_fp32.onnx"},
      {"binary", "/stage/bin/gatewayd", "binary of gatewayd"},
      {"launch config", "/stage/config/launch_manager_config.json", "Launch Manager configuration"},
      {"revision", "/stage/facts/upstream_revision.txt", "upstream revision"},
      {"ldconfig conf", "/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf", "de4sdv-cuda-*.conf"},
      {"diff in sums", "/stage/facts/0002-b.diff", "SHA256SUMS lists 0002-b.diff"},
  };
  for (const Case& c : cases) {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Remove(c.remove);
    ExpectFailure(&fs, Options(), c.fragment, c.what);
  }
}

void TestTheDifferenceIsNeverEmptyAndMatchesItsSums() {
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Remove("/stage/facts/0001-a.diff");
    fs.Remove("/stage/facts/0002-b.diff");
    fs.Remove("/stage/facts/SHA256SUMS");
    ExpectFailure(&fs, Options(), "never empty", "no diff");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/stage/facts/0002-b.diff", "diff --git a/y b/y\n+changed\n");
    ExpectFailure(&fs, Options(), "differs from", "changed diff");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/stage/facts/0001-a.diff", "");
    fs.Remove("/stage/facts/SHA256SUMS");
    ExpectFailure(&fs, Options(), "is empty", "empty diff");
  }
  {  // without SHA256SUMS the diffs are taken as they are
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Remove("/stage/facts/SHA256SUMS");
    id::RecordInputs in;
    std::string error;
    CHECK(id::ResolveInputs(Options(), fs, &in, &error));
  }
}

void TestTheRevisionAndTheLdconfigConf() {
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/stage/facts/upstream_revision.txt", "014e0e7a\n");
    ExpectFailure(&fs, Options(), "40 lowercase hex", "short revision");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    id::RecorderOptions o = Options();
    o.upstream_revision = "ABCDEF0123456789abcdef0123456789abcdef01";
    ExpectFailure(&fs, o, "40 lowercase hex", "upper-case revision");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/etc/ld.so.conf.d/de4sdv-cuda-13.0.conf", "/gpu13\n");
    ExpectFailure(&fs, Options(), "found 2", "two confs");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf", "# nothing\n");
    ExpectFailure(&fs, Options(), "lists no directory", "empty conf");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf", "/nowhere\n");
    ExpectFailure(&fs, Options(), "absent or empty", "missing directory");
  }
  {
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Remove("/gpu/lib/libcudart.so.12.8.90");
    fs.Remove("/gpu/lib/libcudart.so.12");
    fs.Remove("/gpu/lib/libcudnn.so.9");
    fs.Remove("/gpu/lib/libdangling.so");
    ExpectFailure(&fs, Options(), "hold no shared library", "no library");
  }
  {  // an explicit conf needs no search
    FakeFileSystem fs;
    id::test::PutSyntheticStage(&fs);
    fs.Put("/etc/ld.so.conf.d/de4sdv-cuda-13.0.conf", "/gpu13\n");
    id::RecorderOptions o = Options();
    o.ldconfig_conf = "/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf";
    id::RecordInputs in;
    std::string error;
    CHECK(id::ResolveInputs(o, fs, &in, &error));
  }
}

void TestTheCandidateMustBeInTheLaunchConfig() {
  FakeFileSystem fs;
  id::test::PutSyntheticStage(&fs);
  id::RecorderOptions o = Options();
  o.candidate = "someone_else";
  ExpectFailure(&fs, o, "no component someone_else", "candidate");
  FakeFileSystem broken;
  id::test::PutSyntheticStage(&broken);
  broken.Put("/stage/config/launch_manager_config.json", "{\"components\": ");
  ExpectFailure(&broken, Options(), "does not parse", "parse");
  FakeFileSystem precision;
  id::test::PutSyntheticStage(&precision);
  precision.Put("/stage/vision_pilot/config/vision_pilot.conf", "source.mode = score\n");
  ExpectFailure(&precision, Options(), "model.precision", "precision");
}

}  // namespace

int main() {
  TestDefaultsFollowTheRunDirectory();
  TestConfParsing();
  TestLdconfigDirectories();
  TestTheSyntheticStageResolves();
  TestUpstreamsLookupPrefersTheWorkingDirectory();
  TestTheModelPrecisionSelectsTheNetworks();
  TestEveryMissingInputIsAnError();
  TestTheDifferenceIsNeverEmptyAndMatchesItsSums();
  TestTheRevisionAndTheLdconfigConf();
  TestTheCandidateMustBeInTheLaunchConfig();
  return de4sdv::driver_assistance::actuation::test::Finish("record_inputs_test");
}
