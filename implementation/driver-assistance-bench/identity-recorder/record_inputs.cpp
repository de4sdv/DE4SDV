// The identity recorder's input resolution (record_inputs.h). C++17, no S-CORE dependency.
#include "record_inputs.h"

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include "json_lite.h"
#include "sha256.h"

namespace de4sdv::driver_assistance::identity {

namespace json = ::de4sdv::driver_assistance::json;

namespace {

std::string Trim(const std::string& s) {
  const auto a = s.find_first_not_of(" \t\r\n");
  if (a == std::string::npos) return "";
  return s.substr(a, s.find_last_not_of(" \t\r\n") - a + 1);
}

bool EndsWith(const std::string& s, const std::string& suffix) {
  return s.size() >= suffix.size() && s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
}

bool StartsWith(const std::string& s, const std::string& prefix) { return s.compare(0, prefix.size(), prefix) == 0; }

// The merged settings of one component: the component's value over the default's, objects merged key by key.
const json::Value* Member(const json::Value* object, const std::string& key) {
  return object == nullptr ? nullptr : object->Find(key);
}

std::string StringAt(const json::Value* component, const json::Value* defaults, const std::string& section,
                     const std::string& key) {
  const json::Value* own = Member(Member(component, section), key);
  if (own != nullptr && own->IsString()) return own->AsString("");
  const json::Value* fallback = Member(Member(defaults, section), key);
  return fallback != nullptr ? fallback->AsString("") : "";
}

std::vector<std::pair<std::string, std::string>> MergedEnvironment(const json::Value* component,
                                                                   const json::Value* defaults) {
  std::vector<std::pair<std::string, std::string>> merged;
  auto add = [&merged](const json::Value* env) {
    if (env == nullptr || !env->IsObject()) return;
    for (const auto& member : env->members()) {
      bool replaced = false;
      for (auto& kv : merged) {
        if (kv.first == member.first) {
          kv.second = member.second.AsString("");
          replaced = true;
        }
      }
      if (!replaced) merged.emplace_back(member.first, member.second.AsString(""));
    }
  };
  add(Member(Member(defaults, "deployment_config"), "environmental_variables"));
  add(Member(Member(component, "deployment_config"), "environmental_variables"));
  return merged;
}

std::string EnvValue(const LaunchSettings& launch, const std::string& name) {
  for (const auto& kv : launch.environment) {
    if (kv.first == name) return kv.second;
  }
  return "";
}

std::vector<std::string> SplitColons(const std::string& text) {
  std::vector<std::string> parts;
  std::string current;
  for (const char c : text) {
    if (c == ':') {
      if (!current.empty()) parts.push_back(current);
      current.clear();
    } else {
      current += c;
    }
  }
  if (!current.empty()) parts.push_back(current);
  return parts;
}

class Collector {
 public:
  Collector(const FileSystem& fs, std::string* error) : fs_(fs), error_(error) {}

  // Hashes path into list; false (with the error) when it is not a regular file.
  bool Add(std::vector<HashedFile>* list, const std::string& role, const std::string& path) {
    if (seen_.count(path) != 0) return true;
    HashedFile file;
    file.role = role;
    file.path = path;
    if (!fs_.HashFile(path, &file.sha256, &file.bytes)) {
      *error_ = role + ": " + path + " is not a readable regular file";
      return false;
    }
    file.link_target = fs_.LinkTarget(path);
    seen_.insert(path);
    list->push_back(std::move(file));
    return true;
  }

  // Like Add() for a file that may be absent: nothing when absent.
  bool AddIfPresent(std::vector<HashedFile>* list, const std::string& role, const std::string& path) {
    if (!fs_.IsRegularFile(path)) return true;
    return Add(list, role, path);
  }

 private:
  const FileSystem& fs_;
  std::string* error_;
  std::set<std::string> seen_;
};

// upstream's find_config (utils.cpp:3-12): config/<name> in the working directory, else the system copy.
std::string FindConfig(const FileSystem& fs, const RecorderOptions& options, const std::string& working_dir,
                       const std::string& name) {
  const std::string local = JoinPath(working_dir, "config/" + name);
  if (fs.IsRegularFile(local)) return local;
  const std::string system = JoinPath(options.system_root, "config/" + name);
  if (fs.IsRegularFile(system)) return system;
  return "";
}

// upstream's model lookup (inference.cpp:72-73).
std::string FindModel(const FileSystem& fs, const RecorderOptions& options, const std::string& working_dir,
                      const std::string& name) {
  const std::string local = JoinPath(working_dir, "modules/models/weights/" + name);
  if (fs.IsRegularFile(local)) return local;
  const std::string system = JoinPath(options.system_root, "modules/models/weights/" + name);
  if (fs.IsRegularFile(system)) return system;
  return "";
}

bool ReadLaunchSettings(const json::Value& config, std::vector<LaunchSettings>* out, std::string* error) {
  const json::Value* defaults = config.Find("defaults");
  const json::Value* components = config.Find("components");
  if (components == nullptr || !components->IsObject() || components->members().empty()) {
    *error = "the Launch Manager configuration has no components";
    return false;
  }
  for (const auto& member : components->members()) {
    const json::Value* component = &member.second;
    LaunchSettings launch;
    launch.component = member.first;
    const std::string binary = StringAt(component, defaults, "component_properties", "binary_name");
    const std::string bin_dir = StringAt(component, defaults, "deployment_config", "bin_dir");
    if (binary.empty() || bin_dir.empty()) {
      *error = "component " + member.first + " has no binary_name or bin_dir";
      return false;
    }
    launch.binary_path = JoinPath(bin_dir, binary);
    launch.working_dir = StringAt(component, defaults, "deployment_config", "working_dir");
    const json::Value* arguments = Member(Member(component, "component_properties"), "process_arguments");
    if (arguments != nullptr) {
      for (const json::Value& a : arguments->items()) launch.process_arguments.push_back(a.AsString(""));
    }
    launch.environment = MergedEnvironment(component, defaults);
    const json::Value* own_profile = Member(Member(component, "component_properties"), "application_profile");
    const json::Value* default_profile = Member(Member(defaults, "component_properties"), "application_profile");
    const json::Value* type = Member(own_profile, "application_type");
    if (type == nullptr) type = Member(default_profile, "application_type");
    launch.application_type = type != nullptr ? type->AsString("") : "";
    const json::Value* depends = Member(Member(component, "component_properties"), "depends_on");
    if (depends != nullptr) {
      for (const json::Value& d : depends->items()) launch.depends_on.push_back(d.AsString(""));
    }
    out->push_back(std::move(launch));
  }
  return true;
}

bool ReadDiffs(const FileSystem& fs, const std::string& facts_dir, std::vector<DiffFile>* diffs,
               std::string* error) {
  for (const std::string& name : fs.ListDirectory(facts_dir)) {
    if (!EndsWith(name, ".diff")) continue;
    DiffFile diff;
    diff.name = name;
    if (!fs.ReadFile(JoinPath(facts_dir, name), &diff.text)) {
      *error = "source difference " + JoinPath(facts_dir, name) + " is not readable";
      return false;
    }
    if (diff.text.empty()) {
      *error = "source difference " + name + " is empty";
      return false;
    }
    diff.sha256 = Sha256Hex(diff.text);
    diffs->push_back(std::move(diff));
  }
  if (diffs->empty()) {
    *error = "no source difference (*.diff) in " + facts_dir + ": the difference is never empty";
    return false;
  }
  std::string sums;
  if (!fs.ReadFile(JoinPath(facts_dir, "SHA256SUMS"), &sums)) return true;
  std::map<std::string, std::string> listed;
  std::string line;
  for (std::size_t i = 0; i <= sums.size(); ++i) {
    if (i == sums.size() || sums[i] == '\n') {
      const std::string t = Trim(line);
      line.clear();
      if (t.empty()) continue;
      const std::size_t space = t.find(' ');
      if (space == std::string::npos) {
        *error = "malformed line in " + JoinPath(facts_dir, "SHA256SUMS");
        return false;
      }
      std::string name = Trim(t.substr(space));
      if (!name.empty() && name[0] == '*') name.erase(0, 1);
      listed[name] = t.substr(0, space);
    } else {
      line += sums[i];
    }
  }
  for (const DiffFile& diff : *diffs) {
    const auto it = listed.find(diff.name);
    if (it == listed.end() || it->second != diff.sha256) {
      *error = "source difference " + diff.name + " differs from " + JoinPath(facts_dir, "SHA256SUMS");
      return false;
    }
  }
  for (const auto& entry : listed) {
    if (EndsWith(entry.first, ".diff") && !fs.IsRegularFile(JoinPath(facts_dir, entry.first))) {
      *error = "SHA256SUMS lists " + entry.first + ", which is missing from " + facts_dir;
      return false;
    }
  }
  return true;
}

bool HashLibraryDirectory(const FileSystem& fs, Collector* collector, std::vector<HashedFile>* list,
                          const std::string& role, const std::string& directory, bool shared_only,
                          std::size_t* count, std::string* error) {
  const std::vector<std::string> names = fs.ListDirectory(directory);
  if (names.empty()) {
    *error = role + ": directory " + directory + " is absent or empty";
    return false;
  }
  for (const std::string& name : names) {
    if (shared_only && name.find(".so") == std::string::npos) continue;
    const std::string path = JoinPath(directory, name);
    if (!fs.IsRegularFile(path)) continue;  // a dangling link or a subdirectory
    if (!collector->Add(list, role, path)) return false;
    ++*count;
  }
  return true;
}

}  // namespace

void ApplyDefaults(RecorderOptions* options) {
  if (options->stage_root.empty()) options->stage_root = ParentPath(options->run_dir);
  if (options->launch_config.empty()) {
    options->launch_config = JoinPath(options->stage_root, "config/launch_manager_config.json");
  }
  if (options->facts_dir.empty()) options->facts_dir = JoinPath(options->stage_root, "facts");
}

std::map<std::string, std::string> ParseConf(const std::string& text) {
  std::map<std::string, std::string> kv;
  std::string line;
  for (std::size_t i = 0; i <= text.size(); ++i) {
    if (i < text.size() && text[i] != '\n') {
      line += text[i];
      continue;
    }
    std::string t = line;
    line.clear();
    const std::size_t hash = t.find('#');
    if (hash != std::string::npos) t.erase(hash);
    const std::size_t eq = t.find('=');
    if (eq == std::string::npos) continue;
    const std::string key = Trim(t.substr(0, eq));
    std::string value = Trim(t.substr(eq + 1));
    if (!value.empty() && value.back() == ';') value = Trim(value.substr(0, value.size() - 1));
    if (!key.empty()) kv[key] = value;
  }
  return kv;
}

std::vector<std::string> LdconfigDirectories(const std::string& text) {
  std::vector<std::string> directories;
  std::string line;
  for (std::size_t i = 0; i <= text.size(); ++i) {
    if (i < text.size() && text[i] != '\n') {
      line += text[i];
      continue;
    }
    std::string t = line;
    line.clear();
    const std::size_t hash = t.find('#');
    if (hash != std::string::npos) t.erase(hash);
    t = Trim(t);
    if (t.empty() || StartsWith(t, "include ") || !IsAbsolutePath(t)) continue;
    directories.push_back(t);
  }
  return directories;
}

bool ResolveInputs(const RecorderOptions& given, const FileSystem& fs, RecordInputs* inputs, std::string* error) {
  RecorderOptions options = given;
  ApplyDefaults(&options);
  Collector collector(fs, error);

  // The upstream revision.
  std::string revision = options.upstream_revision;
  if (revision.empty()) {
    const std::string path = JoinPath(options.facts_dir, "upstream_revision.txt");
    if (!fs.ReadFile(path, &revision)) {
      *error = "no upstream revision: " + path + " is missing and none was given";
      return false;
    }
  }
  revision = Trim(revision);
  if (!IsLowerHex(revision, 40)) {
    *error = "the upstream revision is not 40 lowercase hex digits: " + revision;
    return false;
  }
  inputs->upstream_revision = revision;

  // The source difference.
  if (!ReadDiffs(fs, options.facts_dir, &inputs->diffs, error)) return false;

  // The launch settings.
  inputs->launch_config_path = options.launch_config;
  if (!fs.ReadFile(options.launch_config, &inputs->launch_config_text)) {
    *error = "the Launch Manager configuration " + options.launch_config + " is not readable";
    return false;
  }
  std::string parse_error;
  const json::Value config = json::Value::Parse(inputs->launch_config_text, &parse_error);
  if (!config.IsObject()) {
    *error = "the Launch Manager configuration does not parse: " + parse_error;
    return false;
  }
  if (!ReadLaunchSettings(config, &inputs->launch, error)) return false;
  const LaunchSettings* candidate = nullptr;
  for (const LaunchSettings& launch : inputs->launch) {
    if (launch.component == options.candidate) candidate = &launch;
  }
  if (candidate == nullptr) {
    *error = "the Launch Manager configuration has no component " + options.candidate;
    return false;
  }
  if (candidate->working_dir.empty()) {
    *error = "the candidate has no working directory";
    return false;
  }
  const std::string& wd = candidate->working_dir;

  // The candidate's own files, in the order the model names them.
  const std::string conf_path = FindConfig(fs, options, wd, "vision_pilot.conf");
  if (conf_path.empty() || !collector.Add(&inputs->configuration, "vision_pilot.conf", conf_path)) {
    if (conf_path.empty()) *error = "vision_pilot.conf: neither " + wd + "/config/ nor the system copy exists";
    return false;
  }
  std::string conf_text;
  fs.ReadFile(conf_path, &conf_text);
  const std::map<std::string, std::string> conf = ParseConf(conf_text);
  inputs->candidate_source_mode = conf.count("source.mode") != 0 ? conf.at("source.mode") : "";
  inputs->candidate_precision = conf.count("model.precision") != 0 ? conf.at("model.precision") : "";
  if (inputs->candidate_precision.empty()) {
    *error = "vision_pilot.conf sets no model.precision, so the networks cannot be named";
    return false;
  }
  for (const char* name : {"H.yaml", "homography_C_matrix.yaml"}) {
    const std::string path = FindConfig(fs, options, wd, name);
    if (path.empty()) {
      *error = std::string(name) + ": neither " + wd + "/config/ nor the system copy exists";
      return false;
    }
    if (!collector.Add(&inputs->configuration, name, path)) return false;
  }
  std::string interface_path = EnvValue(*candidate, "DE4SDV_SCORE_INTERFACE_CONFIG");
  if (interface_path.empty()) interface_path = "config/de4sdv_score_interface.conf";
  if (!IsAbsolutePath(interface_path)) interface_path = JoinPath(wd, interface_path);
  if (!collector.Add(&inputs->configuration, "DE4SDV interface configuration", interface_path)) return false;
  std::string interface_text;
  fs.ReadFile(interface_path, &interface_text);
  const std::map<std::string, std::string> interface_conf = ParseConf(interface_text);
  const auto manifest = interface_conf.find("mw_com.config");
  if (manifest == interface_conf.end() || manifest->second.empty()) {
    *error = "the interface configuration names no mw_com.config";
    return false;
  }
  const std::string manifest_path =
      IsAbsolutePath(manifest->second) ? manifest->second : JoinPath(wd, manifest->second);
  if (!collector.Add(&inputs->configuration, "mw::com manifest of " + options.candidate, manifest_path)) return false;

  // The networks.
  for (const char* net : {"autodrive", "autosteer", "autospeed"}) {
    const std::string name = std::string(net) + "_" + inputs->candidate_precision + ".onnx";
    const std::string path = FindModel(fs, options, wd, name);
    if (path.empty()) {
      *error = "network " + name + ": neither " + wd + "/modules/models/weights/ nor the system copy exists";
      return false;
    }
    if (!collector.Add(&inputs->networks, "network " + std::string(net), path)) return false;
  }

  // The Launch Manager configuration and its serialized form.
  if (!collector.Add(&inputs->configuration, "Launch Manager configuration", options.launch_config)) return false;
  const std::string etc = JoinPath(options.stage_root, "etc");
  for (const std::string& name : fs.ListDirectory(etc)) {
    if (EndsWith(name, ".bin") &&
        !collector.AddIfPresent(&inputs->configuration, "Launch Manager configuration (serialized)",
                                JoinPath(etc, name))) {
      return false;
    }
  }

  // Every file a component's argument or environment names, and every binary.
  for (const LaunchSettings& launch : inputs->launch) {
    for (const std::string& argument : launch.process_arguments) {
      if (IsAbsolutePath(argument) && fs.IsRegularFile(argument) &&
          !collector.Add(&inputs->configuration, "process argument of " + launch.component, argument)) {
        return false;
      }
    }
    for (const auto& kv : launch.environment) {
      if (IsAbsolutePath(kv.second) && fs.IsRegularFile(kv.second) &&
          !collector.Add(&inputs->configuration, kv.first + " of " + launch.component, kv.second)) {
        return false;
      }
    }
  }
  for (const LaunchSettings& launch : inputs->launch) {
    if (!collector.Add(&inputs->binaries, "binary of " + launch.component, launch.binary_path)) return false;
  }

  // The libraries: the candidate's LD_LIBRARY_PATH, then the ldconfig conf of the GPU runtime.
  std::size_t count = 0;
  for (const std::string& directory : SplitColons(EnvValue(*candidate, "LD_LIBRARY_PATH"))) {
    if (!HashLibraryDirectory(fs, &collector, &inputs->runtime_libraries, "LD_LIBRARY_PATH of " + options.candidate,
                              directory, false, &count, error)) {
      return false;
    }
  }
  std::string ldconf = options.ldconfig_conf;
  if (ldconf.empty()) {
    std::vector<std::string> found;
    for (const std::string& name : fs.ListDirectory(options.ldconfig_dir)) {
      if (StartsWith(name, "de4sdv-cuda-") && EndsWith(name, ".conf")) found.push_back(name);
    }
    if (found.size() != 1) {
      *error = "expected one de4sdv-cuda-*.conf in " + options.ldconfig_dir + ", found " +
               std::to_string(found.size());
      return false;
    }
    ldconf = JoinPath(options.ldconfig_dir, found.front());
  }
  inputs->ldconfig_conf_path = ldconf;
  if (!fs.ReadFile(ldconf, &inputs->ldconfig_conf_text)) {
    *error = "the ldconfig conf " + ldconf + " is not readable";
    return false;
  }
  if (!collector.Add(&inputs->configuration, "ldconfig conf of the GPU runtime", ldconf)) return false;
  const std::vector<std::string> directories = LdconfigDirectories(inputs->ldconfig_conf_text);
  if (directories.empty()) {
    *error = "the ldconfig conf " + ldconf + " lists no directory";
    return false;
  }
  std::size_t gpu_libraries = 0;
  for (const std::string& directory : directories) {
    if (!HashLibraryDirectory(fs, &collector, &inputs->runtime_libraries, "named by " + ldconf, directory, true,
                              &gpu_libraries, error)) {
      return false;
    }
  }
  if (gpu_libraries == 0) {
    *error = "the directories of " + ldconf + " hold no shared library";
    return false;
  }
  return true;
}

}  // namespace de4sdv::driver_assistance::identity
