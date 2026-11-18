// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot). See
// score_interface.hpp.
#include "de4sdv/score_interface/score_interface.hpp"

#include <cstdio>
#include <string>
#include <utility>

#include "de4sdv/score_interface/stop_signal.hpp"

namespace de4sdv::score_interface {

std::unique_ptr<ScoreInterface> ScoreInterface::Start() {
  const std::string path = SettingsPath();
  Settings settings;
  std::string error;
  if (!LoadSettings(path, &settings, &error)) {
    std::fprintf(stderr, "[DE4SDV] S-CORE interface: %s\n", error.c_str());
    return nullptr;
  }
  MwComPorts ports = MakeLolaPorts(settings.mw_com_config, &error);
  if (!ports.command || !ports.warning || !ports.record) {
    std::fprintf(stderr, "[DE4SDV] S-CORE interface: mw::com: %s\n", error.c_str());
    return nullptr;
  }
  std::unique_ptr<SimulatorClient> client = MakeCarlaClient(settings.carla);
  std::string off_reason;
  std::unique_ptr<LifecycleClient> lifecycle = MakeLifecycleClient(&off_reason);
  if (!lifecycle) std::fprintf(stderr, "[DE4SDV] S-CORE interface: unsupervised: %s\n", off_reason.c_str());
  auto module = Start(settings, std::move(ports), std::move(client), std::move(lifecycle), off_reason, &error);
  if (!module) std::fprintf(stderr, "[DE4SDV] S-CORE interface: %s\n", error.c_str());
  return module;
}

std::unique_ptr<ScoreInterface> ScoreInterface::Start(const Settings& settings, MwComPorts ports,
                                                      std::unique_ptr<SimulatorClient> client, std::string* error) {
  return Start(settings, std::move(ports), std::move(client), nullptr, "no lifecycle client given", error);
}

namespace {

// A reason as a JSON string body: quotes, backslashes and control characters escaped.
std::string Escaped(const std::string& text) {
  std::string out;
  for (const char c : text) {
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if (static_cast<unsigned char>(c) < 0x20) {
      char buf[8];
      std::snprintf(buf, sizeof buf, "\\u%04x", static_cast<unsigned>(static_cast<unsigned char>(c)));
      out += buf;
    } else {
      out += c;
    }
  }
  return out;
}

}  // namespace

std::unique_ptr<ScoreInterface> ScoreInterface::Start(const Settings& settings, MwComPorts ports,
                                                      std::unique_ptr<SimulatorClient> client,
                                                      std::unique_ptr<LifecycleClient> lifecycle,
                                                      const std::string& off_reason, std::string* error) {
  if (!ports.command || !ports.warning || !ports.record || !client) {
    *error = "a port or the simulator client is missing";
    return nullptr;
  }
  std::unique_ptr<ScoreInterface> m(new ScoreInterface());
  if (!settings.log_path.empty()) {
    m->log_file_ = std::fopen(settings.log_path.c_str(), "a");
    if (m->log_file_ == nullptr) {
      *error = "cannot open log.path " + settings.log_path;
      return nullptr;
    }
    ScoreInterface* self = m.get();
    m->log_ = [self](const std::string& line) { self->Log(line); };
  }
  m->ports_ = std::move(ports);
  m->client_ = std::move(client);
  m->gate_ = std::make_unique<CandidateRecordGate>(m->ports_.record.get(), m->log_);
  m->command_writer_ =
      std::make_unique<DrivingCommandWriter>(m->ports_.command.get(), m->gate_.get(), &m->clock_, m->log_);
  m->warning_writer_ = std::make_unique<WarningRequestWriter>(m->ports_.warning.get(), &m->clock_, m->log_);
  m->camera_ = std::make_shared<ScoreCameraInterface>(&m->clock_, m->log_);
  SimulatorClient* raw_client = m->client_.get();
  m->vehicle_ = std::make_shared<ScoreVehicleInterface>(
      [raw_client](EgoVelocity* v) { return raw_client->NewestEgoVelocity(v); }, m->command_writer_.get(), m->log_);
  m->publisher_ = std::make_unique<ScoreWarningRequestPublisher>(m->warning_writer_.get());
  m->lifecycle_ = std::move(lifecycle);
  m->supervision_ = std::make_unique<CycleSupervision>(m->lifecycle_.get(), m->log_);

  if (!m->client_->Attach(error)) return nullptr;
  ScoreCameraInterface* camera = m->camera_.get();
  if (!m->client_->Start([camera](const CameraImageView& image) { camera->OnImage(image); }, error)) {
    return nullptr;
  }
  m->camera_->SetOpen(true);
  m->Log(std::string("{\"kind\":\"start\",\"mono_ns\":") + std::to_string(MonotonicNs()) +
         ",\"real_ns\":" + std::to_string(RealtimeNs()) + "}");
  if (!m->lifecycle_) {
    m->Log("{\"kind\":\"supervision.off\",\"reason\":\"" + Escaped(off_reason) + "\",\"mono_ns\":" +
           std::to_string(MonotonicNs()) + ",\"real_ns\":" + std::to_string(RealtimeNs()) + "}");
  }
  return m;
}

void ScoreInterface::CycleCompleted() {
  if (supervision_) supervision_->CycleCompleted(StopRequested());
}

ScoreInterface::~ScoreInterface() {
  if (supervision_) supervision_->Stop();  // no alive notification after this
  if (client_) client_->Stop();  // no image callback after this
  const std::string summary = Summary();
  std::fprintf(stderr, "[DE4SDV] S-CORE interface summary %s\n", summary.c_str());
  Log(summary);
  if (log_file_ != nullptr) std::fclose(log_file_);
}

void ScoreInterface::Log(const std::string& line) {
  std::lock_guard<std::mutex> lock(log_mutex_);
  if (log_file_ == nullptr) return;
  std::fputs(line.c_str(), log_file_);
  std::fputc('\n', log_file_);
  std::fflush(log_file_);
}

std::string ScoreInterface::Summary() const {
  const CameraStats cs = camera_ ? camera_->get_camera_stats() : CameraStats{};
  const DrivingCommandWriter::Counters cc = command_writer_ ? command_writer_->counters() : DrivingCommandWriter::Counters{};
  const WarningRequestWriter::Counters wc = warning_writer_ ? warning_writer_->counters() : WarningRequestWriter::Counters{};
  std::string s = "{\"kind\":\"summary\"";
  s += ",\"images_received\":" + std::to_string(cs.frames_received);
  s += ",\"images_dropped\":" + std::to_string(cs.frames_dropped);
  s += ",\"images_handed_on\":" + std::to_string(cs.frames_captured);
  s += ",\"image_conversion_errors\":" + std::to_string(cs.conversion_errors);
  s += ",\"commands_sent\":" + std::to_string(cc.sent);
  s += ",\"commands_send_failed\":" + std::to_string(cc.send_failed);
  s += ",\"commands_withheld_before_record\":" + std::to_string(cc.withheld_before_record);
  s += ",\"commands_withheld_without_capture_time\":" + std::to_string(cc.withheld_without_capture_time);
  s += ",\"candidate_records_rejected\":" + std::to_string(gate_ ? gate_->rejected() : 0);
  s += ",\"warning_events_sent\":" + std::to_string(wc.sent);
  s += ",\"warning_events_requested\":" + std::to_string(wc.requested);
  s += ",\"warning_events_send_failed\":" + std::to_string(wc.send_failed);
  s += ",\"warning_events_not_encodable\":" + std::to_string(wc.not_encodable);
  s += ",\"speed_unavailable\":" + std::to_string(vehicle_ ? vehicle_->speed_unavailable() : 0);
  s += ",\"alive_reported\":" + std::to_string(supervision_ ? supervision_->alive_reported() : 0);
  s += ",\"mono_ns\":" + std::to_string(MonotonicNs()) + "}";
  return s;
}

}  // namespace de4sdv::score_interface
