// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
// See score_camera_interface.hpp, score_vehicle_interface.hpp and score_warning_request_publisher.hpp.
#include <algorithm>
#include <cstdio>
#include <string>

#include "de4sdv/score_interface/score_camera_interface.hpp"
#include "de4sdv/score_interface/score_vehicle_interface.hpp"
#include "de4sdv/score_interface/score_warning_request_publisher.hpp"

namespace de4sdv::score_interface {

namespace {

std::string ImageLine(const char* kind, std::uint64_t frame, double sim_time_s) {
  char sim[32];
  std::snprintf(sim, sizeof sim, "%.17g", sim_time_s);
  return std::string("{\"kind\":\"") + kind + "\",\"frame\":" + std::to_string(frame) + ",\"sim_s\":" + sim +
         ",\"mono_ns\":" + std::to_string(MonotonicNs()) + "}";
}

}  // namespace

// ── SCORECameraInterface (MAP-DRIVING-DA-CAMERA-IMAGE) ──────────────────────────────────────────────────────────

ScoreCameraInterface::ScoreCameraInterface(PassClock* clock, LineLog log) : clock_(clock), log_(std::move(log)) {}

void ScoreCameraInterface::OnImage(const CameraImageView& image) {
  if (image.width <= 0 || image.height <= 0) {
    conversion_errors_.fetch_add(1);
    return;
  }
  Frame f;
  f.bgr.create(image.height, image.width, CV_8UC3);  // continuous
  if (!ConvertBgraToBgr(image, f.bgr.data, f.bgr.total() * f.bgr.elemSize())) {
    conversion_errors_.fetch_add(1);
    if (log_) log_(ImageLine("error.camera_image", image.frame, image.sim_time_s));
    return;
  }
  f.frame = image.frame;
  f.sim_time_s = image.sim_time_s;
  width_.store(static_cast<std::uint32_t>(image.width));
  height_.store(static_cast<std::uint32_t>(image.height));
  if (log_) log_(ImageLine("in.camera_image", image.frame, image.sim_time_s));
  Frame replaced;
  if (slot_.Put(std::move(f), &replaced) && log_) {
    log_(ImageLine("drop.camera_image", replaced.frame, replaced.sim_time_s));
  }
}

cv::Mat ScoreCameraInterface::get_latest_frame() {
  Frame f;
  if (!slot_.Take(&f)) return cv::Mat();
  clock_->valid = true;  // the capture time of this pass (loop thread only)
  clock_->capture_time_s = f.sim_time_s;
  clock_->frame = f.frame;
  handed_on_.fetch_add(1);
  if (log_) log_(ImageLine("pass.camera_image", f.frame, f.sim_time_s));
  return f.bgr;
}

CameraStats ScoreCameraInterface::get_camera_stats() const {
  CameraStats s{};
  s.frames_captured = handed_on_.load();  // handed on to the loop
  s.capture_errors = 0;
  s.current_width = width_.load();
  s.current_height = height_.load();
  s.current_fps = 0.0;  // the simulator paces the images in simulation time
  s.frames_received = slot_.received();
  s.frames_dropped = slot_.dropped();
  s.conversion_errors = conversion_errors_.load();
  return s;
}

// ── SCOREVehicleInterface (MAP-DRIVING-DA-VEHICLE-SPEED, MAP-DRIVING-DA-COMMAND) ────────────────────────────────

ScoreVehicleInterface::ScoreVehicleInterface(SpeedSource speed_source, DrivingCommandWriter* writer, LineLog log)
    : speed_source_(std::move(speed_source)), writer_(writer), log_(std::move(log)) {}

double ScoreVehicleInterface::read() {
  EgoVelocity v;
  if (!speed_source_ || !speed_source_(&v)) {
    ++speed_unavailable_;
    return 0.0;
  }
  const double speed = SpeedOf(v);
  if (log_) {
    char text[96];
    std::snprintf(text, sizeof text, "\"speed_mps\":%.17g,\"sim_s\":%.17g", speed, v.sim_time_s);
    log_(std::string("{\"kind\":\"in.vehicle_speed\",") + text + ",\"frame\":" + std::to_string(v.frame) +
         ",\"mono_ns\":" + std::to_string(MonotonicNs()) + "}");
  }
  return speed;
}

void ScoreVehicleInterface::write(double steering, double acceleration) { writer_->Write(steering, acceleration); }

// ── SCOREWarningRequestPublisher (MAP-DRIVING-DA-WARNING-REQUEST) ───────────────────────────────────────────────

bool HoldsForwardCollisionWarningOrEmergencyBraking(const std::vector<Warning>& warnings) {
  return std::any_of(warnings.begin(), warnings.end(),
                     [](Warning w) { return w == Warning::FCW || w == Warning::AEB; });
}

ScoreWarningRequestPublisher::ScoreWarningRequestPublisher(WarningRequestWriter* writer) : writer_(writer) {}

void ScoreWarningRequestPublisher::Publish(const Plan& plan) {
  writer_->Write(HoldsForwardCollisionWarningOrEmergencyBraking(plan.warnings));
}

}  // namespace de4sdv::score_interface
