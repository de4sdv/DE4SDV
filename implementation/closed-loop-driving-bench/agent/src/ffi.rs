//! The C ABI of the agent's C++ libraries (cc/agent_ffi.h).

use crate::messages::{ConditionMsg, EgoMsg, InputsMsg, ModeMsg, PlanMsg, ValidPlanMsg};
use core::ffi::c_char;

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct AbiSizes {
    pub plan_payload: u32,
    pub mode_payload: u32,
    pub inputs: u32,
    pub condition: u32,
    pub ego: u32,
    pub plan_msg: u32,
    pub valid_plan_msg: u32,
    pub mode_msg: u32,
}

extern "C" {
    pub fn de4sdv_abi_sizes() -> AbiSizes;
    pub fn de4sdv_agent_init(config_path: *const c_char) -> i32;
    pub fn de4sdv_agent_fini();

    pub fn de4sdv_condition_startup() -> i32;
    pub fn de4sdv_condition_step(inputs: *mut InputsMsg, condition: *mut ConditionMsg, ego: *mut EgoMsg) -> i32;
    pub fn de4sdv_condition_shutdown();

    pub fn de4sdv_infer_startup() -> i32;
    pub fn de4sdv_infer_step(inputs: *const InputsMsg, plan: *mut PlanMsg) -> i32;
    pub fn de4sdv_infer_shutdown();

    pub fn de4sdv_supervise_startup() -> i32;
    pub fn de4sdv_supervise_step(
        condition: *const ConditionMsg,
        plan: *const PlanMsg,
        valid_plan: *mut ValidPlanMsg,
        mode: *mut ModeMsg,
    ) -> i32;
    pub fn de4sdv_supervise_shutdown();

    pub fn de4sdv_command_startup() -> i32;
    pub fn de4sdv_command_step(ego: *const EgoMsg, valid_plan: *const ValidPlanMsg, mode: *const ModeMsg) -> i32;
    pub fn de4sdv_command_shutdown();
}
