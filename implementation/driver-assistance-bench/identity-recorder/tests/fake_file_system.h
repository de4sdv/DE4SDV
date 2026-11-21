// An in-memory FileSystem for the identity recorder's tests: files by absolute path, symbolic links by path.
#pragma once

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "file_system.h"
#include "sha256.h"

namespace de4sdv::driver_assistance::identity::test {

class FakeFileSystem final : public FileSystem {
 public:
  void Put(const std::string& path, const std::string& content) { files_[path] = content; }
  void Link(const std::string& path, const std::string& target) { links_[path] = target; }
  void Remove(const std::string& path) {
    files_.erase(path);
    links_.erase(path);
  }
  void MakeDirectory(const std::string& path) { directories_.insert(path); }

  bool ReadFile(const std::string& path, std::string* out) const override {
    const std::string resolved = Resolve(path);
    const auto it = files_.find(resolved);
    if (it == files_.end()) return false;
    *out = it->second;
    return true;
  }
  bool IsRegularFile(const std::string& path) const override { return files_.count(Resolve(path)) != 0; }
  bool HashFile(const std::string& path, std::string* sha256_hex, std::uint64_t* size) const override {
    std::string content;
    if (!ReadFile(path, &content)) return false;
    *sha256_hex = Sha256Hex(content);
    *size = content.size();
    ++hashed_;
    return true;
  }
  std::vector<std::string> ListDirectory(const std::string& directory) const override {
    std::set<std::string> names;
    const std::string prefix = directory.back() == '/' ? directory : directory + "/";
    auto take = [&](const std::string& path) {
      if (path.compare(0, prefix.size(), prefix) != 0) return;
      const std::string rest = path.substr(prefix.size());
      const std::size_t slash = rest.find('/');
      names.insert(slash == std::string::npos ? rest : rest.substr(0, slash));
    };
    for (const auto& f : files_) take(f.first);
    for (const auto& l : links_) take(l.first);
    for (const auto& d : directories_) take(d);
    return std::vector<std::string>(names.begin(), names.end());
  }
  std::string LinkTarget(const std::string& path) const override {
    const auto it = links_.find(path);
    return it == links_.end() ? "" : it->second;
  }
  int hashed() const { return hashed_; }

 private:
  std::string Resolve(const std::string& path) const {
    std::string current = path;
    for (int hops = 0; hops < 8; ++hops) {
      const auto it = links_.find(current);
      if (it == links_.end()) return current;
      current = IsAbsolutePath(it->second) ? it->second : JoinPath(ParentPath(current), it->second);
    }
    return current;
  }

  std::map<std::string, std::string> files_;
  std::map<std::string, std::string> links_;
  std::set<std::string> directories_;
  mutable int hashed_ = 0;
};

// A synthetic stage like the one start_score_side.sh lays out under /tmp/de4sdv-da-bench, built from invented
// contents (no model text, no upstream file).
inline void PutSyntheticStage(FakeFileSystem* fs, const std::string& root = "/stage") {
  fs->Put(root + "/config/launch_manager_config.json", R"({
  "schema_version": 2,
  "defaults": {
    "deployment_config": {"bin_dir": ")" + root + R"(/bin", "working_dir": ")" + root + R"(",
      "environmental_variables": {"LD_LIBRARY_PATH": ")" + root + R"(/lib", "SHARED": "default"}},
    "component_properties": {"application_profile": {"application_type": "Native"}}
  },
  "components": {
    "identity_recorder": {"component_properties": {"binary_name": "identity_recorder",
        "application_profile": {"application_type": "Reporting"},
        "process_arguments": ["--run-dir", ")" + root + R"(/run"]},
      "deployment_config": {"environmental_variables": {"MW_COM_CONFIG": ")" + root +
                       R"(/config/mw_com_config_identity_recorder.json"}}},
    "gatewayd": {"component_properties": {"binary_name": "gatewayd",
        "process_arguments": ["-c", ")" + root + R"(/config/gateway.bin", "-s", ")" + root +
                       R"(/config/mw_com_config_gatewayd.json"]}},
    "vision_pilot": {"component_properties": {"binary_name": "vision_pilot", "depends_on": ["identity_recorder"],
        "application_profile": {"application_type": "Reporting_And_Supervised"}},
      "deployment_config": {"working_dir": ")" + root + R"(/vision_pilot",
        "environmental_variables": {"SHARED": "own", "DE4SDV_SCORE_INTERFACE_CONFIG": ")" + root +
                       R"(/config/de4sdv_score_interface.conf"}}}
  }
})");
  fs->Put(root + "/config/mw_com_config_identity_recorder.json", "{\"recorder\":1}");
  fs->Put(root + "/config/mw_com_config_gatewayd.json", "{\"gatewayd\":1}");
  fs->Put(root + "/config/mw_com_config_vision_pilot.json", "{\"candidate\":1}");
  fs->Put(root + "/config/gateway.bin", std::string("\x01\x02\x00\x03", 4));
  fs->Put(root + "/config/de4sdv_score_interface.conf",
          "# synthetic\nmw_com.config = " + root + "/config/mw_com_config_vision_pilot.json\ncarla.host = none\n");
  fs->Put(root + "/vision_pilot/config/vision_pilot.conf",
          "source.mode = score   # synthetic\nmodel.precision = fp32\nspeed_limit = 5.0;\n");
  fs->Put(root + "/vision_pilot/config/H.yaml", "H: synthetic-h\n");
  fs->Put(root + "/vision_pilot/config/homography_C_matrix.yaml", "C: synthetic-c\n");
  for (const char* net : {"autodrive", "autosteer", "autospeed"}) {
    fs->Put(root + "/vision_pilot/modules/models/weights/" + net + "_fp32.onnx", std::string("onnx-") + net);
    fs->Put(root + "/vision_pilot/modules/models/weights/" + net + "_int8.onnx", std::string("int8-") + net);
  }
  for (const char* bin : {"identity_recorder", "gatewayd", "vision_pilot"}) {
    fs->Put(root + "/bin/" + bin, std::string("ELF-") + bin);
  }
  fs->Put(root + "/lib/libonnxruntime.so.1", "ort");
  fs->Link(root + "/lib/libonnxruntime.so", "libonnxruntime.so.1");
  fs->Put(root + "/facts/0001-a.diff", "diff --git a/x b/x\n+one\n");
  fs->Put(root + "/facts/0002-b.diff", "diff --git a/y b/y\n+two\n");
  fs->Put(root + "/facts/SHA256SUMS", Sha256Hex("diff --git a/x b/x\n+one\n") + "  0001-a.diff\n" +
                                          Sha256Hex("diff --git a/y b/y\n+two\n") + "  0002-b.diff\n");
  fs->Put(root + "/facts/upstream_revision.txt", "0123456789abcdef0123456789abcdef01234567\n");
  fs->MakeDirectory(root + "/run");
  fs->Put("/etc/ld.so.conf.d/de4sdv-cuda-12.8.1.conf", "# synthetic\n/gpu/lib\n");
  fs->Put("/etc/ld.so.conf.d/other.conf", "/elsewhere\n");
  fs->Put("/gpu/lib/libcudart.so.12.8.90", "cudart");
  fs->Link("/gpu/lib/libcudart.so.12", "libcudart.so.12.8.90");
  fs->Put("/gpu/lib/libcudnn.so.9", "cudnn");
  fs->Put("/gpu/lib/LICENSE", "not a library");
  fs->Link("/gpu/lib/libdangling.so", "missing.so");
}

}  // namespace de4sdv::driver_assistance::identity::test
