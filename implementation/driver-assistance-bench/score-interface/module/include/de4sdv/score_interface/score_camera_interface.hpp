// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// SCORECameraInterface of the model: upstream's camera seam (camera_interface.hpp:18, get_latest_frame) fed by the
// CARLA 1.0 client (MAP-DRIVING-DA-CAMERA-IMAGE). The client's thread calls OnImage(); the module converts the
// image from BGRA to BGR there and keeps only the newest one. get_latest_frame() hands it on to the loop
// (vision_pilot.cpp:117) and sets the pass's capture time, the simulation time of the world snapshot the image was
// rendered in. Every image replaced unread is counted and logged as dropped.
#pragma once

#include <atomic>
#include <cstdint>

#include <camera_interface/camera_interface.hpp>
#include <opencv2/core/mat.hpp>

#include "de4sdv/score_interface/core.hpp"
#include "de4sdv/score_interface/seams.hpp"

namespace de4sdv::score_interface {

class ScoreCameraInterface : public camera_interface::CameraInterface {
 public:
  ScoreCameraInterface(PassClock* clock, LineLog log);
  ~ScoreCameraInterface() override = default;

  // On the simulator client's thread.
  void OnImage(const CameraImageView& image);
  void SetOpen(bool open) { open_.store(open); }

  bool is_device_open() const override { return open_.load(); }
  // An empty Mat when no new image arrived since the last call; the pass clock is left as it is then.
  cv::Mat get_latest_frame() override;
  CameraStats get_camera_stats() const override;

 private:
  struct Frame {
    cv::Mat bgr;
    std::uint64_t frame = 0;
    double sim_time_s = 0.0;
  };
  PassClock* clock_;
  LineLog log_;
  LatestSlot<Frame> slot_;
  std::atomic<bool> open_{false};
  std::atomic<std::uint64_t> handed_on_{0};
  std::atomic<std::uint64_t> conversion_errors_{0};
  std::atomic<std::uint32_t> width_{0};
  std::atomic<std::uint32_t> height_{0};
};

}  // namespace de4sdv::score_interface
