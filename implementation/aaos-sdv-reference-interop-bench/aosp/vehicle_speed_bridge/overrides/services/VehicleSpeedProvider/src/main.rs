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

//! Lifecycle-managed reference publisher for the generated Vehicle.Speed bundle.
//!
//! This is a deterministic reference source, not a VSS hardware binding. The
//! runtime proof must replace `reference_vehicle_speed_message` with a real
//! source before claiming production or vehicle interoperability.

use de4sdv_reference_vehicle_speed_proto::vehicle_speed::{
    vehicle_speed::Quality,
    VehicleSpeed,
};
use log::{debug, error, info, warn};
use sdv::mw::{clientlib, Communicate, SdvComms};
use sdv::status::{SdvResult, SdvStatus, SdvStatusCode};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;
use tokio_util::sync::CancellationToken;

sdv::lifecycle::register_service_bundle!(VehicleSpeedProviderServiceBundle);

struct VehicleSpeedProviderServiceBundle {
    cancellation_token: Option<CancellationToken>,
    context: ContextRef,
}

impl ServiceBundle for VehicleSpeedProviderServiceBundle {
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
        debug!("on_start called for Vehicle.Speed provider");
        let context = self.context;
        let cancellation_token = CancellationToken::new();
        self.cancellation_token = Some(cancellation_token.clone());
        let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .enable_io()
            .build()
        else {
            panic!("failed to start the Vehicle.Speed provider runtime");
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
                error!("Vehicle.Speed provider loop stopped: {result:?}");
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

async fn sdv_main(comms: Arc<dyn Communicate>) -> SdvResult<()> {
    info!("Starting VehicleSpeedProvider");

    sdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_provider::VehicleSpeedProvider::builder()
        .set_comms(comms.clone())
        .build()
        .await
        .map_err(|error| {
            SdvStatus::with_message(SdvStatusCode::Internal, error.to_string())
        })?;

    let publisher = clientlib::create_publisher(
        comms.as_ref(),
        sdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_provider::PublisherDescriptors::<VehicleSpeed>::VEHICLE_SPEED,
    )
    .await?;

    let mut sequence = 0_u64;
    loop {
        let message = reference_vehicle_speed_message(sequence);
        info!(
            "DE4SDV_VEHICLE_SPEED_PUBLISHED speed_kmh={} timestamp_ns={}",
            message.speed_kmh, message.timestamp_ns
        );
        publisher.publish(&message)?;
        sequence = sequence.saturating_add(1);
        sleep(Duration::from_secs(1)).await;
    }
}

fn reference_vehicle_speed_message(timestamp_ns: u64) -> VehicleSpeed {
    VehicleSpeed {
        speed_kmh: 36.0,
        timestamp_ns,
        quality: ::protobuf::EnumOrUnknown::new(Quality::VALID),
        ..Default::default()
    }
}
