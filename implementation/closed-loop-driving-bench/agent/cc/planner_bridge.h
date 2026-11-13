// DE4SDV closed-loop driving bench: drivingAgent's embedded CPython (DESIGN.md, inferPlan). One
// interpreter in the process, started on FEO worker 40 by inferPlan's startup; conditionInputs and
// inferPlan call it from the same worker, each call under the GIL (PyGILState_Ensure/Release).
// The Python side is the de4sdv_planner package (agent/python).
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace de4sdv::driving::agent {

class PlannerBridge {
 public:
  struct Identity {
    bool refused = false;
    std::string reason;    // "no_pin" | "mismatch" | ""
    std::string expected;  // 64 hex or ""
    std::string actual;    // 64 hex or ""
  };
  struct ConditionIn {
    std::uint64_t frame = 0;
    const std::uint8_t* image[6] = {};  // BGRA; nullptr = missing
    std::size_t image_bytes[6] = {};
    int width[6] = {};
    int height[6] = {};
    double world_from_vehicle[16] = {};  // UE, row-major
    const float* map_context = nullptr;
    std::size_t map_bytes = 0;
    const float* route_mask = nullptr;
    std::size_t route_bytes = 0;
  };
  struct ConditionOut {
    bool primed = false;
    bool has_rows = false;
    float measured[64][4] = {};
    float checkpoint[64][4] = {};
    std::string record_json;
  };
  struct InferOut {
    bool planned = false;
    float samples[64][5] = {};  // acceleration, curvature, x, y, heading
    float v0 = 0.0f;
    std::string record_json;
  };

  // Starts the interpreter from the venv's python (its pyvenv.cfg puts the venv on sys.path),
  // prepends `paths` to sys.path, imports de4sdv_planner and runs setup(setup_json). The identity
  // check of REQ-DRIVING-035 is the first thing setup does; on a refusal nothing else is loaded.
  bool Start(const std::string& python_executable, const std::vector<std::string>& paths,
             const std::string& setup_json, Identity* identity, std::string* setup_result_json, std::string* error);
  bool SetRig(const std::string& rig_json, std::string* result_json, std::string* error);
  // Binds the engine to the calling thread. The harness's persistent no_grad + bf16 autocast region
  // is thread-local, so inferPlan's startup calls this on FEO worker 40, the thread of every later
  // condition and infer call; Start runs earlier, on the main thread, before FEO starts.
  bool BindThread(std::string* result_json, std::string* error);
  // ICD section 8: de4sdv_planner.write_run_record, once before the first plan;
  // *result_json = {"path", "sha256", "identity"}.
  bool WriteRunRecord(const std::string& path, const std::string& fields_json, std::string* result_json,
                      std::string* error);
  bool Condition(const ConditionIn& in, ConditionOut* out, std::string* error);
  bool Infer(std::uint64_t frame, InferOut* out, std::string* error);
  // inferPlan while the agent primes (DESIGN.md, warm-up while priming): de4sdv_planner.warm; *record_json is the
  // engine's warm-up record to log, empty when there is nothing to log.
  bool Warm(std::uint64_t frame, std::string* record_json, std::string* error);
  void Stop();
  bool started() const { return started_; }

 private:
  void* module_ = nullptr;      // PyObject*
  void* main_state_ = nullptr;  // PyThreadState* saved after setup
  bool started_ = false;       // setup accepted the checkpoint: condition and infer may run
  bool module_ready_ = false;  // setup returned (refused or not): the run record may be written
};

}  // namespace de4sdv::driving::agent
