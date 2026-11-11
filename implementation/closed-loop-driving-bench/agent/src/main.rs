//! drivingAgent (INC-DRIVING-001 phase 8, slice 10b): one FEO primary agent (direct mpsc
//! signalling), four activities in one chain on worker 40, paced by the frame events of the input
//! side (FEO_PACE_SOCKET, the DE4SDV event-trigger patch of the scheduler). See DESIGN.md.
//!
//! Usage: driving_agent <agent_config.json>

mod activities;
mod ffi;
mod messages;

use activities::{CommandVehicle, ConditionInputs, InferPlan, SuperviseLoop};
use feo::activity::{ActivityBuilder, ActivityIdAndBuilder};
use feo::agent::com_init::initialize_com_primary;
use feo::agent::direct::primary_mpsc::{Primary, PrimaryConfig};
use feo::ids::{ActivityId, AgentId, WorkerId};
use feo::topicspec::{Direction, TopicSpecification};
use feo_com::interface::ComBackend;
use feo_log::{error, info, LevelFilter};
use feo_time::Duration;
use messages::*;
use std::collections::HashMap;
use std::ffi::CString;

const AGENT_ID: AgentId = AgentId::new(100);
const WORKER: u64 = 40;

fn worker_assignments() -> Vec<(WorkerId, Vec<ActivityIdAndBuilder>)> {
    vec![(
        WORKER.into(),
        vec![
            (0.into(), Box::new(|id| ConditionInputs::build(id)) as Box<dyn ActivityBuilder>),
            (1.into(), Box::new(|id| InferPlan::build(id)) as Box<dyn ActivityBuilder>),
            (2.into(), Box::new(|id| SuperviseLoop::build(id)) as Box<dyn ActivityBuilder>),
            (3.into(), Box::new(|id| CommandVehicle::build(id)) as Box<dyn ActivityBuilder>),
        ],
    )]
}

fn assignment_ids() -> HashMap<AgentId, Vec<(WorkerId, Vec<ActivityId>)>> {
    [(AGENT_ID, vec![(WORKER.into(), vec![0.into(), 1.into(), 2.into(), 3.into()])])].into_iter().collect()
}

/// dependencies: 1 <- 0, 2 <- 1, 3 <- 2 and 3 <- 0 (the ego sample)
fn activity_dependencies() -> HashMap<ActivityId, Vec<ActivityId>> {
    [
        (0.into(), vec![]),
        (1.into(), vec![0.into()]),
        (2.into(), vec![1.into()]),
        (3.into(), vec![2.into(), 0.into()]),
    ]
    .into_iter()
    .collect()
}

fn topic_dependencies<'a>() -> Vec<TopicSpecification<'a>> {
    use Direction::*;
    vec![
        TopicSpecification::new::<InputsMsg>(TOPIC_INPUTS, vec![(0.into(), Outgoing), (1.into(), Incoming)]),
        TopicSpecification::new::<ConditionMsg>(TOPIC_CONDITION, vec![(0.into(), Outgoing), (2.into(), Incoming)]),
        TopicSpecification::new::<EgoMsg>(TOPIC_EGO, vec![(0.into(), Outgoing), (3.into(), Incoming)]),
        TopicSpecification::new::<PlanMsg>(TOPIC_PLAN, vec![(1.into(), Outgoing), (2.into(), Incoming)]),
        TopicSpecification::new::<ValidPlanMsg>(TOPIC_VALID_PLAN, vec![(2.into(), Outgoing), (3.into(), Incoming)]),
        TopicSpecification::new::<ModeMsg>(TOPIC_MODE, vec![(2.into(), Outgoing), (3.into(), Incoming)]),
    ]
}

fn main() {
    feo_logger::init(LevelFilter::Info, true, true);
    let config_path = match std::env::args().nth(1) {
        Some(p) => p,
        None => {
            error!("usage: driving_agent <agent_config.json>");
            std::process::exit(2);
        }
    };

    let sizes = unsafe { ffi::de4sdv_abi_sizes() };
    if let Err(diff) = check_abi(&sizes) {
        error!("drivingAgent: C/Rust message layouts differ: {diff}");
        std::process::exit(3);
    }

    let c_path = CString::new(config_path.clone()).expect("config path without NUL");
    if unsafe { ffi::de4sdv_agent_init(c_path.as_ptr()) } != 0 {
        error!("drivingAgent: init failed ({config_path})");
        std::process::exit(4);
    }
    info!("drivingAgent: initialised from {config_path}; pace socket {:?}", std::env::var("FEO_PACE_SOCKET").ok());

    // Initialize topics. Do not drop.
    let _topic_guards = initialize_com_primary(ComBackend::LinuxShm, AGENT_ID, topic_dependencies(), &assignment_ids(), 0);

    let config = PrimaryConfig {
        id: AGENT_ID,
        // Unused while FEO_PACE_SOCKET is set: the frame events pace the chain.
        cycle_time: Duration::from_millis(100),
        activity_dependencies: activity_dependencies(),
        recorder_ids: vec![],
        worker_assignments: worker_assignments(),
        timeout: Duration::from_secs(5),
        // FEO waits for each ready signal with `timeout`; `startup_timeout` only bounds the whole
        // startup. So no activity's startup may take 5 s: the checkpoint's load, compile, warm-up
        // and parity run in de4sdv_agent_init, before the primary starts.
        startup_timeout: Duration::from_secs(30),
    };

    let result = Primary::new(config)
        .unwrap_or_else(|err| {
            error!("drivingAgent: failed to initialise the primary: {err:?}");
            unsafe { ffi::de4sdv_agent_fini() };
            std::process::exit(5);
        })
        .run();
    unsafe { ffi::de4sdv_agent_fini() };
    if let Err(err) = result {
        error!("drivingAgent: primary ended with {err:?}");
        std::process::exit(6);
    }
}
