// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): the C ABI between the FEO Rust
// shells of drivingAgent (src/*.rs) and its C++ libraries. The six message structs are the FEO
// topic payloads; src/messages.rs mirrors them field by field (#[repr(C)]). Their sizes are checked
// at startup (de4sdv_abi_sizes) and the agent refuses to start on a difference.
//
// Return codes: 0 = done; 1 = nothing new this step (not an error); < 0 = failure (the shell
// returns ActivityError).
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// == de4sdv::driving::PlanSample / DrivingPlanPayload / DrivingModePayload (static_assert in the .cpp).
typedef struct {
  float acceleration;
  float curvature;
  float x;
  float y;
  float heading;
} De4sdvPlanSample;

typedef struct {
  uint64_t frameIndex;
  double captureTime;
  double productionTime;
  float horizon;
  uint32_t sampleCount;
  De4sdvPlanSample samples[64];
  char producer[64];
  char runRecord[64];
  char planReference[64];
} De4sdvPlanPayload;

typedef struct {
  uint8_t mode;
  uint8_t cause;
  uint8_t reserved[6];
  uint64_t frameIndex;
  double captureTime;
  double decisionTime;
  char checkpointExpectedSha256[64];
  char checkpointActualSha256[64];
  char refusalReason[16];
} De4sdvModePayload;

// Topic driving/inputs: conditionInputs -> inferPlan. The tensors stay with the embedded planner; the
// message names the step, its priming and its input-condition word (no inference on a faulted step).
typedef struct {
  uint64_t step_frame;
  uint32_t has_step;        // 1: a ready slot was taken this step
  uint32_t primed;          // 1: camera and ego-motion histories are complete
  uint32_t condition_bits;  // 1u << Cause per input cause (REQ-DRIVING-023 to -025)
  uint32_t slot_token;      // reserved: conditionInputs releases its frame-store slot after conditioning
  float speed_mps;          // speed at the step (the integration's initial speed)
  uint32_t reserved;
} De4sdvInputsMsg;

// Topic driving/condition: conditionInputs -> superviseLoop.
typedef struct {
  uint64_t step_frame;
  uint32_t has_step;
  uint32_t condition_bits;
  uint32_t primed;
  float speed_kmh;  // newest motion sample, VSS km/h (standstill below 0.1 km/h)
} De4sdvConditionMsg;

// Topic driving/ego: conditionInputs -> commandVehicle.
typedef struct {
  uint64_t frame;
  uint32_t has_sample;
  float speed_kmh;
} De4sdvEgoMsg;

// Topic driving/plan: inferPlan -> superviseLoop.
typedef struct {
  uint32_t has_plan;
  uint32_t new_this_step;
  De4sdvPlanPayload plan;
} De4sdvPlanMsg;

// Topic driving/valid_plan: superviseLoop -> commandVehicle (the newest valid plan).
typedef struct {
  uint32_t has_plan;
  uint32_t reserved;
  De4sdvPlanPayload plan;
} De4sdvValidPlanMsg;

// Topic driving/mode: superviseLoop -> commandVehicle.
typedef struct {
  uint32_t changed;
  uint32_t stop_began;
  De4sdvModePayload mode;
} De4sdvModeMsg;

typedef struct {
  uint32_t plan_payload;
  uint32_t mode_payload;
  uint32_t inputs;
  uint32_t condition;
  uint32_t ego;
  uint32_t plan_msg;
  uint32_t valid_plan_msg;
  uint32_t mode_msg;
} De4sdvAbiSizes;

De4sdvAbiSizes de4sdv_abi_sizes(void);

// Process: configuration, run logs, mw::com runtime and the four skeletons (offered at once, before
// the planner's long setup, so the actuation adapter and the state publisher find them).
int32_t de4sdv_agent_init(const char* config_path);
void de4sdv_agent_fini(void);

int32_t de4sdv_condition_startup(void);
int32_t de4sdv_condition_step(De4sdvInputsMsg* inputs, De4sdvConditionMsg* condition, De4sdvEgoMsg* ego);
void de4sdv_condition_shutdown(void);

int32_t de4sdv_infer_startup(void);
int32_t de4sdv_infer_step(const De4sdvInputsMsg* inputs, De4sdvPlanMsg* plan);
void de4sdv_infer_shutdown(void);

int32_t de4sdv_supervise_startup(void);
int32_t de4sdv_supervise_step(const De4sdvConditionMsg* condition, const De4sdvPlanMsg* plan,
                              De4sdvValidPlanMsg* valid_plan, De4sdvModeMsg* mode);
void de4sdv_supervise_shutdown(void);

int32_t de4sdv_command_startup(void);
int32_t de4sdv_command_step(const De4sdvEgoMsg* ego, const De4sdvValidPlanMsg* valid_plan,
                            const De4sdvModeMsg* mode);
void de4sdv_command_shutdown(void);

#ifdef __cplusplus
}  // extern "C"
#endif
