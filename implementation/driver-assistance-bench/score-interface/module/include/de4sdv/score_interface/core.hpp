// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The module's logic, free of upstream types, OpenCV, mw::com and CARLA. The adapters on upstream's seams
// (score_camera_interface.hpp, score_vehicle_interface.hpp, score_warning_request_publisher.hpp) delegate to it.
#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <utility>

#include "de4sdv/driver_assistance/payloads.h"
#include "de4sdv/score_interface/seams.hpp"

namespace de4sdv::score_interface {

// One JSON object per line; empty when the run keeps no event log.
using LineLog = std::function<void(const std::string&)>;

// The capture time of the frame of the current pass of the loop (MAP-DRIVING-DA-CAMERA-IMAGE: "the module keeps its
// capture time ... and the vehicle interface and the warning request publisher read it in the same pass"). Only the
// loop thread touches it: the camera interface sets it when get_latest_frame() hands on an image, the vehicle
// interface and the warning request publisher read it later in that pass.
struct PassClock {
  bool valid = false;
  double capture_time_s = 0.0;  // simulation s
  std::uint64_t frame = 0;      // the simulator's frame number of the image
};

// A single slot that keeps only the newest item. Put() replaces an unread item and counts it as dropped, as
// upstream's ROS 2 camera interface counts a replaced frame (camera_ros2_interface.cpp:95-100). Put() runs on the
// producer's thread, Take() on the loop's.
template <typename T>
class LatestSlot {
 public:
  // Returns true when the item replaced an unread one; that one goes to *replaced if given.
  bool Put(T item, T* replaced = nullptr) {
    std::lock_guard<std::mutex> lock(mutex_);
    ++received_;
    const bool dropped = full_;
    if (dropped) {
      ++dropped_;
      if (replaced != nullptr) *replaced = std::move(item_);
    }
    item_ = std::move(item);
    full_ = true;
    return dropped;
  }
  bool Take(T* out) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!full_) return false;
    *out = std::move(item_);
    item_ = T{};
    full_ = false;
    return true;
  }
  std::uint64_t received() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return received_;
  }
  std::uint64_t dropped() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return dropped_;
  }

 private:
  mutable std::mutex mutex_;
  T item_{};
  bool full_ = false;
  std::uint64_t received_ = 0;
  std::uint64_t dropped_ = 0;
};

// BGRA to BGR, no resampling (MAP-DRIVING-DA-CAMERA-IMAGE transformationRule). dst holds 3 * width * height bytes,
// rows without padding. Returns false, writing nothing, for a size it cannot convert.
bool ConvertBgraToBgr(const CameraImageView& image, std::uint8_t* dst, std::size_t dst_bytes);

// |velocity| in m/s, the value VehicleInterface::read() returns (MAP-DRIVING-DA-VEHICLE-SPEED: the planner takes
// m/s; the km/h value is the VSS typing at the port).
double SpeedOf(const EgoVelocity& velocity);

// steeringAngle = -steering[1] * 180 / pi (MAP-DRIVING-DA-COMMAND): the candidate's steering is a tyre angle in rad
// in the sign of CARLA's steer, positive to the right; the VSS steering angle is in degrees, positive to the left.
float SteeringAngleDegrees(double steering_rad);

// One driving command with its check value (payloads.h, DrivingCommandCheckValue).
driver_assistance::DrivingCommandEventPayload MakeDrivingCommand(double steering_rad, double acceleration,
                                                                 double issue_time_s, std::uint32_t sequence_count);

// The gate of REQ-DRIVING-044: open once a well-formed candidate record has arrived on its mw::com subscription,
// and open from then on. Well-formed: NUL-terminated strings, 64 hex digits of SHA-256, 40 hex digits of revision,
// a difference of more than 0 bytes (payloads.h: "never 0").
class CandidateRecordGate {
 public:
  CandidateRecordGate(CandidateRecordSource* source, LineLog log);
  bool Open();  // polls the source while closed
  std::uint64_t rejected() const { return rejected_; }

 private:
  CandidateRecordSource* source_;
  LineLog log_;
  bool open_ = false;
  std::uint64_t rejected_ = 0;
};

bool WellFormedCandidateRecord(const driver_assistance::CandidateRecordEventPayload& record);

// The write of the vehicle interface (MAP-DRIVING-DA-COMMAND): adds issueTime (the capture time of the pass), a
// sequence count from 1 in each run and the check value, and sends nothing before the record has arrived.
class DrivingCommandWriter {
 public:
  struct Counters {
    std::uint64_t sent = 0;
    std::uint64_t send_failed = 0;               // the sequence count was used: the adapter sees a loss
    std::uint64_t withheld_before_record = 0;
    std::uint64_t withheld_without_capture_time = 0;
  };
  DrivingCommandWriter(DrivingCommandSink* sink, CandidateRecordGate* gate, const PassClock* clock, LineLog log);
  // Returns true when a command was handed to the sink and the sink accepted it.
  bool Write(double steering_rad, double acceleration);
  const Counters& counters() const { return counters_; }

 private:
  DrivingCommandSink* sink_;
  CandidateRecordGate* gate_;
  const PassClock* clock_;
  LineLog log_;
  std::uint32_t last_sequence_ = 0;
  Counters counters_{};
};

// The warning request publisher's core (MAP-DRIVING-DA-WARNING-REQUEST): one event per plan, issueTime the capture
// time of the pass, the 8 bytes of EncodeWarningRequestSomeip.
class WarningRequestWriter {
 public:
  struct Counters {
    std::uint64_t sent = 0;
    std::uint64_t requested = 0;  // events sent with requested = true
    std::uint64_t send_failed = 0;
    std::uint64_t not_encodable = 0;  // no capture time, or one EncodeWarningRequestSomeip refuses
  };
  WarningRequestWriter(WarningRequestSink* sink, const PassClock* clock, LineLog log);
  bool Write(bool requested);
  const Counters& counters() const { return counters_; }

 private:
  WarningRequestSink* sink_;
  const PassClock* clock_;
  LineLog log_;
  Counters counters_{};
};

// Monotonic and real time of the host, ns, for the event log (the path share of REQ-DRIVING-042 is wall-clock).
std::int64_t MonotonicNs();
std::int64_t RealtimeNs();

}  // namespace de4sdv::score_interface
