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
//! The observer records raw received VehicleSpeed messages through logcat. It
//! does not reuse provider state or assert a ROS 2/Autoware result.

use de4sdv_reference_vehicle_speed_proto::vehicle_speed::VehicleSpeed;
use futures::Stream;
use futures_util::stream::StreamExt;
use log::{debug, error, info, warn};
use sdv::mw::{clientlib, Availability, Communicate, SdvComms, SubscribeOptions};
use sdv::status::{SdvResult, SdvStatus, SdvStatusCode};
use std::pin::Pin;
use std::sync::Arc;
use tokio_util::sync::CancellationToken;

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

    let observer = clientlib::create_observer(
        comms.as_ref(),
        descriptor,
        &SubscribeOptions::default(),
    )
    .await?;
    handle_vehicle_speed_observer(observer).await;
    Ok(())
}

async fn handle_vehicle_speed_observer(
    mut observer: Pin<Box<dyn Stream<Item = SdvResult<Vec<VehicleSpeed>>> + Send>>,
) {
    while let Some(batch) = observer.next().await {
        match batch {
            Ok(messages) => {
                for message in messages {
                    info!(
                        "DE4SDV_VEHICLE_SPEED_OBSERVED speed_kmh={} timestamp_ns={}",
                        message.speed_kmh, message.timestamp_ns
                    );
                }
            }
            Err(error) => error!("Vehicle.Speed observer receive error: {error:?}"),
        }
    }
}
