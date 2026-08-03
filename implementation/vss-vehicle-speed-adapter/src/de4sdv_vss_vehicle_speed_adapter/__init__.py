"""DE4SDV provider-neutral VSS Vehicle.Speed adapter."""

from .adapter import (
    AdapterConfig,
    NormalizedVehicleSpeed,
    SampleValidationError,
    SignalQuality,
    VehicleSpeedProvider,
    VehicleSpeedSample,
    VelocityConsumer,
    VssVehicleSpeedAdapter,
)

__all__ = [
    "AdapterConfig",
    "NormalizedVehicleSpeed",
    "SampleValidationError",
    "SignalQuality",
    "VehicleSpeedProvider",
    "VehicleSpeedSample",
    "VelocityConsumer",
    "VssVehicleSpeedAdapter",
]
