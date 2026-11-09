//! FEO topic messages of drivingAgent: field-by-field mirrors of the C structs in cc/agent_ffi.h.
//! The C side reports its sizes (de4sdv_abi_sizes); `check_abi` refuses to start on a difference.

use crate::ffi::AbiSizes;
use core::mem::size_of;

pub const TOPIC_INPUTS: &str = "driving/inputs";
pub const TOPIC_CONDITION: &str = "driving/condition";
pub const TOPIC_EGO: &str = "driving/ego";
pub const TOPIC_PLAN: &str = "driving/plan";
pub const TOPIC_VALID_PLAN: &str = "driving/valid_plan";
pub const TOPIC_MODE: &str = "driving/mode";

macro_rules! zeroed_default {
    ($t:ty) => {
        impl Default for $t {
            fn default() -> Self {
                // SAFETY: plain-old-data of integers, floats and byte arrays; all-zero is valid.
                unsafe { core::mem::zeroed() }
            }
        }
    };
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct PlanSample {
    pub acceleration: f32,
    pub curvature: f32,
    pub x: f32,
    pub y: f32,
    pub heading: f32,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct PlanPayload {
    pub frame_index: u64,
    pub capture_time: f64,
    pub production_time: f64,
    pub horizon: f32,
    pub sample_count: u32,
    pub samples: [PlanSample; 64],
    pub producer: [u8; 64],
    pub run_record: [u8; 64],
    pub plan_reference: [u8; 64],
}
zeroed_default!(PlanPayload);

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ModePayload {
    pub mode: u8,
    pub cause: u8,
    pub reserved: [u8; 6],
    pub frame_index: u64,
    pub capture_time: f64,
    pub decision_time: f64,
    pub checkpoint_expected_sha256: [u8; 64],
    pub checkpoint_actual_sha256: [u8; 64],
    pub refusal_reason: [u8; 16],
}
zeroed_default!(ModePayload);

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct InputsMsg {
    pub step_frame: u64,
    pub has_step: u32,
    pub primed: u32,
    pub condition_bits: u32,
    pub slot_token: u32,
    pub speed_mps: f32,
    pub reserved: u32,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct ConditionMsg {
    pub step_frame: u64,
    pub has_step: u32,
    pub condition_bits: u32,
    pub primed: u32,
    pub speed_kmh: f32,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct EgoMsg {
    pub frame: u64,
    pub has_sample: u32,
    pub speed_kmh: f32,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct PlanMsg {
    pub has_plan: u32,
    pub new_this_step: u32,
    pub plan: PlanPayload,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct ValidPlanMsg {
    pub has_plan: u32,
    pub reserved: u32,
    pub plan: PlanPayload,
}

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct ModeMsg {
    pub changed: u32,
    pub stop_began: u32,
    pub mode: ModePayload,
}

/// Compares the Rust layout with the C layout; Err names every difference.
pub fn check_abi(c: &AbiSizes) -> Result<(), String> {
    let pairs = [
        ("plan_payload", c.plan_payload as usize, size_of::<PlanPayload>()),
        ("mode_payload", c.mode_payload as usize, size_of::<ModePayload>()),
        ("inputs", c.inputs as usize, size_of::<InputsMsg>()),
        ("condition", c.condition as usize, size_of::<ConditionMsg>()),
        ("ego", c.ego as usize, size_of::<EgoMsg>()),
        ("plan_msg", c.plan_msg as usize, size_of::<PlanMsg>()),
        ("valid_plan_msg", c.valid_plan_msg as usize, size_of::<ValidPlanMsg>()),
        ("mode_msg", c.mode_msg as usize, size_of::<ModeMsg>()),
    ];
    let bad: Vec<String> = pairs
        .iter()
        .filter(|(_, c_size, rust_size)| c_size != rust_size)
        .map(|(name, c_size, rust_size)| format!("{name}: C {c_size} != Rust {rust_size}"))
        .collect();
    if bad.is_empty() {
        Ok(())
    } else {
        Err(bad.join(", "))
    }
}
