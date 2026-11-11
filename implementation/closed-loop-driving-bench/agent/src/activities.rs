//! The four FEO activities of drivingAgent (DESIGN.md): Rust shells that move the FEO topic messages
//! and call the C++ libraries through the C ABI. One chain per frame event, all on worker 40.

use crate::ffi;
use crate::messages::*;
use feo::activity::Activity;
use feo::error::ActivityError;
use feo::ids::ActivityId;
use feo_com::interface::{ActivityInput, ActivityOutput};
use feo_com::linux_shm::{LinuxShmInput, LinuxShmOutput};
use feo_log::error;

fn input<T: core::fmt::Debug + 'static>(topic: &str) -> Box<dyn ActivityInput<T>> {
    Box::new(LinuxShmInput::new(topic))
}

fn output<T: core::fmt::Debug + 'static>(topic: &str) -> Box<dyn ActivityOutput<T>> {
    Box::new(LinuxShmOutput::new(topic))
}

fn read_or_default<T: Copy + Default + core::fmt::Debug>(inp: &dyn ActivityInput<T>) -> T {
    match inp.read() {
        Ok(guard) => *guard,
        Err(_) => T::default(),
    }
}

fn send<T: core::fmt::Debug>(out: &mut dyn ActivityOutput<T>, value: T, what: &str) -> Result<(), ActivityError> {
    match out.write_uninit() {
        Ok(guard) => guard.write_payload(value).send().map_err(|e| {
            error!("drivingAgent: send on {what} failed: {e:?}");
            ActivityError::Step
        }),
        Err(e) => {
            error!("drivingAgent: write_uninit on {what} failed: {e:?}");
            Err(ActivityError::Step)
        }
    }
}

fn check(rc: i32, what: &str, err: ActivityError) -> Result<(), ActivityError> {
    if rc < 0 {
        error!("drivingAgent: {what} returned {rc}");
        Err(err)
    } else {
        Ok(())
    }
}

/// 0 conditionInputs: newest ready frame -> inputs, condition, ego (+ mw::com ego_motion_sample).
pub struct ConditionInputs {
    id: ActivityId,
    out_inputs: Box<dyn ActivityOutput<InputsMsg>>,
    out_condition: Box<dyn ActivityOutput<ConditionMsg>>,
    out_ego: Box<dyn ActivityOutput<EgoMsg>>,
}

impl ConditionInputs {
    pub fn build(id: ActivityId) -> Box<dyn Activity> {
        Box::new(Self {
            id,
            out_inputs: output(TOPIC_INPUTS),
            out_condition: output(TOPIC_CONDITION),
            out_ego: output(TOPIC_EGO),
        })
    }
}

impl Activity for ConditionInputs {
    fn id(&self) -> ActivityId {
        self.id
    }
    fn startup(&mut self) -> Result<(), ActivityError> {
        check(unsafe { ffi::de4sdv_condition_startup() }, "condition_startup", ActivityError::Startup)
    }
    fn step(&mut self) -> Result<(), ActivityError> {
        let (mut i, mut c, mut e) = (InputsMsg::default(), ConditionMsg::default(), EgoMsg::default());
        check(unsafe { ffi::de4sdv_condition_step(&mut i, &mut c, &mut e) }, "condition_step", ActivityError::Step)?;
        send(self.out_inputs.as_mut(), i, TOPIC_INPUTS)?;
        send(self.out_condition.as_mut(), c, TOPIC_CONDITION)?;
        send(self.out_ego.as_mut(), e, TOPIC_EGO)
    }
    fn shutdown(&mut self) -> Result<(), ActivityError> {
        unsafe { ffi::de4sdv_condition_shutdown() };
        Ok(())
    }
}

/// 1 inferPlan: inputs -> plan (+ mw::com plan).
pub struct InferPlan {
    id: ActivityId,
    in_inputs: Box<dyn ActivityInput<InputsMsg>>,
    out_plan: Box<dyn ActivityOutput<PlanMsg>>,
}

impl InferPlan {
    pub fn build(id: ActivityId) -> Box<dyn Activity> {
        Box::new(Self { id, in_inputs: input(TOPIC_INPUTS), out_plan: output(TOPIC_PLAN) })
    }
}

impl Activity for InferPlan {
    fn id(&self) -> ActivityId {
        self.id
    }
    fn startup(&mut self) -> Result<(), ActivityError> {
        check(unsafe { ffi::de4sdv_infer_startup() }, "infer_startup", ActivityError::Startup)
    }
    fn step(&mut self) -> Result<(), ActivityError> {
        let i = read_or_default(self.in_inputs.as_ref());
        let mut p = PlanMsg::default();
        check(unsafe { ffi::de4sdv_infer_step(&i, &mut p) }, "infer_step", ActivityError::Step)?;
        send(self.out_plan.as_mut(), p, TOPIC_PLAN)
    }
    fn shutdown(&mut self) -> Result<(), ActivityError> {
        unsafe { ffi::de4sdv_infer_shutdown() };
        Ok(())
    }
}

/// 2 superviseLoop: condition + plan -> valid_plan + mode (+ mw::com mode).
pub struct SuperviseLoop {
    id: ActivityId,
    in_condition: Box<dyn ActivityInput<ConditionMsg>>,
    in_plan: Box<dyn ActivityInput<PlanMsg>>,
    out_valid_plan: Box<dyn ActivityOutput<ValidPlanMsg>>,
    out_mode: Box<dyn ActivityOutput<ModeMsg>>,
}

impl SuperviseLoop {
    pub fn build(id: ActivityId) -> Box<dyn Activity> {
        Box::new(Self {
            id,
            in_condition: input(TOPIC_CONDITION),
            in_plan: input(TOPIC_PLAN),
            out_valid_plan: output(TOPIC_VALID_PLAN),
            out_mode: output(TOPIC_MODE),
        })
    }
}

impl Activity for SuperviseLoop {
    fn id(&self) -> ActivityId {
        self.id
    }
    fn startup(&mut self) -> Result<(), ActivityError> {
        check(unsafe { ffi::de4sdv_supervise_startup() }, "supervise_startup", ActivityError::Startup)
    }
    fn step(&mut self) -> Result<(), ActivityError> {
        let c = read_or_default(self.in_condition.as_ref());
        let p = read_or_default(self.in_plan.as_ref());
        let (mut v, mut m) = (ValidPlanMsg::default(), ModeMsg::default());
        check(unsafe { ffi::de4sdv_supervise_step(&c, &p, &mut v, &mut m) }, "supervise_step", ActivityError::Step)?;
        send(self.out_valid_plan.as_mut(), v, TOPIC_VALID_PLAN)?;
        send(self.out_mode.as_mut(), m, TOPIC_MODE)
    }
    fn shutdown(&mut self) -> Result<(), ActivityError> {
        unsafe { ffi::de4sdv_supervise_shutdown() };
        Ok(())
    }
}

/// 3 commandVehicle: ego + valid_plan + mode -> mw::com command.
pub struct CommandVehicle {
    id: ActivityId,
    in_ego: Box<dyn ActivityInput<EgoMsg>>,
    in_valid_plan: Box<dyn ActivityInput<ValidPlanMsg>>,
    in_mode: Box<dyn ActivityInput<ModeMsg>>,
}

impl CommandVehicle {
    pub fn build(id: ActivityId) -> Box<dyn Activity> {
        Box::new(Self {
            id,
            in_ego: input(TOPIC_EGO),
            in_valid_plan: input(TOPIC_VALID_PLAN),
            in_mode: input(TOPIC_MODE),
        })
    }
}

impl Activity for CommandVehicle {
    fn id(&self) -> ActivityId {
        self.id
    }
    fn startup(&mut self) -> Result<(), ActivityError> {
        check(unsafe { ffi::de4sdv_command_startup() }, "command_startup", ActivityError::Startup)
    }
    fn step(&mut self) -> Result<(), ActivityError> {
        let e = read_or_default(self.in_ego.as_ref());
        let v = read_or_default(self.in_valid_plan.as_ref());
        let m = read_or_default(self.in_mode.as_ref());
        check(unsafe { ffi::de4sdv_command_step(&e, &v, &m) }, "command_step", ActivityError::Step)
    }
    fn shutdown(&mut self) -> Result<(), ActivityError> {
        unsafe { ffi::de4sdv_command_shutdown() };
        Ok(())
    }
}
