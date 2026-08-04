from pathlib import Path


BENCH = Path(__file__).parents[1]
BRIDGE = BENCH / "aosp" / "vehicle_speed_bridge"
CATALOG = BENCH / "contract"
PROVIDER = BRIDGE / "overrides" / "services" / "VehicleSpeedProvider"
OBSERVER = BRIDGE / "overrides" / "services" / "VehicleSpeedObserver"
GENERATOR = BRIDGE / "stage_aosp_bridge.sh"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing bridge artifact: {path}"
    return path.read_text()


def test_catalog_declares_publisher_and_independent_subscriber():
    text = _read(CATALOG / "vehicle_speed.vsidl")

    assert 'package: "de4sdv.reference.vehicle_speed"' in text
    assert 'name: "VehicleSpeedProvider"' in text
    assert 'name: "VehicleSpeedObserver"' in text
    assert 'message: "VehicleSpeed"' in text
    assert 'topic: "vehicle-speed"' in text
    assert text.count("publisher {") == 1
    assert text.count("subscriber {") == 1


def test_provider_is_lifecycle_managed_and_uses_generated_publisher_descriptor():
    source = _read(PROVIDER / "src" / "main.rs")

    assert "register_service_bundle!(VehicleSpeedProviderServiceBundle)" in source
    assert "impl ServiceBundle for VehicleSpeedProviderServiceBundle" in source
    assert "clientlib::create_publisher" in source
    assert "PublisherDescriptors::<VehicleSpeed>::VEHICLE_SPEED" in source
    assert "EnumOrUnknown::new(Quality::VALID)" in source
    assert "libsdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_provider" in _read(GENERATOR)
    assert "libsdv_lm_vehicle_speed_provider" in _read(GENERATOR)
    assert "libde4sdv_reference_vehicle_speed_proto" in _read(CATALOG / "Android.bp")
    assert "--genrule --services --apex" in _read(GENERATOR)


def test_observer_waits_for_discovery_and_records_independent_messages():
    source = _read(OBSERVER / "src" / "main.rs")

    assert "register_service_bundle!(VehicleSpeedObserverServiceBundle)" in source
    assert "create_registration_event_stream" in source
    assert "Availability::Available" in source
    assert "clientlib::create_observer" in source
    assert "SubscriberDescriptors::<VehicleSpeed>::VEHICLE_SPEED" in source
    assert "libsdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_observer" in _read(GENERATOR)
    assert "libsdv_lm_vehicle_speed_observer" in _read(GENERATOR)
    assert "generated output" in _read(BRIDGE / "README.md").lower()


def test_bridge_readme_keeps_runtime_and_ros_claims_evidence_gated():
    text = _read(BRIDGE / "README.md")

    assert "not proven" in text.lower()
    assert "service discovery" in text.lower()
    assert "ROS 2" in text
    assert "generated output is deliberately not committed" in text.lower()
