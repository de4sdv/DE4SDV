// Copyright (C) 2026 DE4SDV contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

//! Lifecycle-managed independent observer for the generated Vehicle.Speed bundle.
//!
//! The observer records raw received VehicleSpeed messages through logcat. The
//! structured log record is the default campaign transport because the
//! service-bundle SELinux domain does not have a network socket permission.
//! Direct TCP egress remains an explicit opt-in for a product policy that
//! grants that capability; it is not enabled by default.

use de4sdv_reference_vehicle_speed_proto::vehicle_speed::{
    vehicle_speed::Quality,
    VehicleSpeed,
};
use futures::Stream;
use futures_util::stream::StreamExt;
use log::{debug, error, info, warn};
use sdv::mw::{clientlib, Availability, Communicate, SdvComms, SubscribeOptions};
use sdv::status::{SdvResult, SdvStatus, SdvStatusCode};
use std::io::Write;
use std::net::TcpStream;
use std::pin::Pin;
use std::sync::mpsc::{self, Sender};
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tokio_util::sync::CancellationToken;

const WIRE_SCHEMA: &str = "de4sdv.reference.vehicle_speed.VehicleSpeed";
const WIRE_CLOCK_DOMAIN: &str = "aaos-unix-time-ns";

sdv::lifecycle::register_service_bundle!(VehicleSpeedObserverServiceBundle);

struct VehicleSpeedObserverServiceBundle {
    cancellation_token: Option<CancellationToken>,
    context: ContextRef,
}

impl ServiceBundle for VehicleSpeedObserverServiceBundle {
    fn new(context: ContextRef) -> Self {
        if let Err(err) = sdv::tracing::try_init_tracing() {
            warn!("Failed to initialize service-bundle tracing: {err}");
        }
        Self {
            cancellation_token: None,
            context,
        }
    }

    fn on_start(&mut self) {
        debug!("on_start called for Vehicle.Speed observer");
        let context = self.context;
        let cancellation_token = CancellationToken::new();
        self.cancellation_token = Some(cancellation_token.clone());
        let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .enable_io()
            .build()
        else {
            panic!("failed to start the Vehicle.Speed observer runtime");
        };

        std::thread::spawn(move || {
            runtime.block_on(async move {
                let comms = Arc::new(SdvComms { context });
                let result = tokio::select! {
                    result = sdv_main(comms) => result,
                    () = cancellation_token.cancelled() => Err(
                        SdvStatus::new(SdvStatusCode::Cancelled),
                    ),
                };
                error!("Vehicle.Speed observer loop stopped: {result:?}");
            });
        });
    }

    fn on_stop(&mut self) {
        self.cancellation_token
            .as_mut()
            .expect("on_start must create the cancellation token")
            .cancel();
        self.cancellation_token = None;
    }
}

async fn wait_for_publisher_to_be_available(
    comms: &dyn Communicate,
    descriptor: &clientlib::SubscriberDescriptor<VehicleSpeed>,
) -> SdvResult<()> {
    let mut events = clientlib::create_registration_event_stream(comms, descriptor).await?;
    while let Some(event) = events.next().await {
        match event {
            Availability::Available => return Ok(()),
            Availability::Unavailable => debug!("Vehicle.Speed publisher is unavailable"),
        }
    }
    Err(SdvStatus::with_message(
        SdvStatusCode::Unavailable,
        "Vehicle.Speed publisher registration stream ended",
    ))
}

async fn sdv_main(comms: Arc<dyn Communicate>) -> SdvResult<()> {
    info!("Starting VehicleSpeedObserver");

    sdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_observer::VehicleSpeedObserver::builder()
        .set_comms(comms.clone())
        .build()
        .await
        .map_err(|error| {
            SdvStatus::with_message(SdvStatusCode::Internal, error.to_string())
        })?;

    let descriptor = sdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_observer::SubscriberDescriptors::<VehicleSpeed>::VEHICLE_SPEED;
    wait_for_publisher_to_be_available(comms.as_ref(), descriptor).await?;

    let egress = std::env::var("DE4SDV_VEHICLE_SPEED_EGRESS_ENDPOINT")
        .ok()
        .filter(|endpoint| !endpoint.trim().is_empty())
        .map(spawn_tcp_egress);
    let observer = clientlib::create_observer(
        comms.as_ref(),
        descriptor,
        &SubscribeOptions::default(),
    )
    .await?;
    handle_vehicle_speed_observer(observer, egress.as_ref()).await;
    drop(egress);
    Ok(())
}

fn spawn_tcp_egress(endpoint: String) -> Sender<String> {
    let (sender, receiver) = mpsc::channel::<String>();

    thread::spawn(move || {
        let mut stream: Option<TcpStream> = None;
        let mut pending: Option<String> = None;
        while let Some(line) = pending.take().or_else(|| receiver.recv().ok()) {
            loop {
                if stream.is_none() {
                    match TcpStream::connect(&endpoint) {
                        Ok(candidate) => {
                            if let Err(error) = candidate.set_nodelay(true) {
                                warn!("Vehicle.Speed TCP egress could not set TCP_NODELAY: {error}");
                            }
                            info!("Vehicle.Speed TCP egress connected endpoint={endpoint}");
                            stream = Some(candidate);
                        }
                        Err(error) => {
                            warn!("Vehicle.Speed TCP egress connect failed endpoint={endpoint} error={error}");
                            pending = Some(line);
                            thread::sleep(Duration::from_millis(250));
                            break;
                        }
                    }
                }

                let Some(candidate) = stream.as_mut() else {
                    continue;
                };
                match candidate.write_all(line.as_bytes()) {
                    Ok(()) => break,
                    Err(error) => {
                        warn!("Vehicle.Speed TCP egress write failed error={error}");
                        stream = None;
                        pending = Some(line);
                        thread::sleep(Duration::from_millis(250));
                        break;
                    }
                }
            }
        }
    });

    sender
}

async fn handle_vehicle_speed_observer(
    mut observer: Pin<Box<dyn Stream<Item = SdvResult<Vec<VehicleSpeed>>> + Send>>,
    egress: Option<&Sender<String>>,
) {
    while let Some(batch) = observer.next().await {
        match batch {
            Ok(messages) => {
                for message in messages {
                    info!(
                        "DE4SDV_VEHICLE_SPEED_OBSERVED speed_kmh={} timestamp_ns={}",
                        message.speed_kmh, message.timestamp_ns
                    );
                    if message.quality
                        == ::protobuf::EnumOrUnknown::new(
                            Quality::VALID,
                        )
                    {
                        let wire_message = format!(
                            "{{\"schema\":\"{WIRE_SCHEMA}\",\"speed_kmh\":{},\"timestamp_ns\":{},\"quality\":\"VALID\",\"clock_domain\":\"{WIRE_CLOCK_DOMAIN}\"}}\n",
                            message.speed_kmh, message.timestamp_ns
                        );
                        info!(
                            "DE4SDV_VEHICLE_SPEED_WIRE {}",
                            wire_message.trim_end()
                        );
                        if let Some(egress) = egress {
                            if let Err(error) = egress.send(wire_message) {
                                error!("Vehicle.Speed TCP egress queue stopped: {error}");
                            }
                        }
                    } else {
                        warn!("Vehicle.Speed observer suppressed non-VALID sample");
                    }
                }
            }
            Err(error) => error!("Vehicle.Speed observer receive error: {error:?}"),
        }
    }
}
