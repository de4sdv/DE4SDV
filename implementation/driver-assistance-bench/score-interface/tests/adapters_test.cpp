// Unit tests of the DE4SDV S-CORE interface's adapters on upstream's seams (camera_interface.hpp,
// vehicle_interface.hpp, types.hpp at 014e0e7a) and of the module as the loop uses it (score_interface.hpp), with
// fakes for mw::com and the CARLA 1.0 client. The two factories of seams.hpp are defined below as fakes, in place
// of src/lola_bindings.cpp and src/carla_client.cpp.
//
// Build (test_score_interface.py): g++ -std=c++17 against upstream's headers extracted from the pin, OpenCV 4 and
// the bench's interfaces/include; links the module's portable sources and opencv_core.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include "de4sdv/score_interface/score_interface.hpp"
#include "fakes.hpp"

namespace da = de4sdv::driver_assistance;
namespace si = de4sdv::score_interface;

static int failures = 0;
#define EXPECT(cond)                                              \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      ++failures;                                                 \
    }                                                             \
  } while (0)

// The fakes the no-argument Start() gets from the two factories.
static fakes::CommandSink* g_command = nullptr;
static fakes::WarningSink* g_warning = nullptr;
static fakes::RecordSource* g_record = nullptr;
static fakes::SimulatorClient* g_client = nullptr;
static std::string g_mw_com_config;
static si::CarlaSettings g_carla;

namespace de4sdv::score_interface {
std::unique_ptr<SimulatorClient> MakeCarlaClient(const CarlaSettings& settings) {
  g_carla = settings;
  auto c = std::make_unique<fakes::SimulatorClient>();
  g_client = c.get();
  return c;
}
MwComPorts MakeLolaPorts(const std::string& mw_com_config_path, std::string* /*error*/) {
  g_mw_com_config = mw_com_config_path;
  MwComPorts p;
  auto c = std::make_unique<fakes::CommandSink>();
  auto w = std::make_unique<fakes::WarningSink>();
  auto r = std::make_unique<fakes::RecordSource>();
  g_command = c.get();
  g_warning = w.get();
  g_record = r.get();
  p.command = std::move(c);
  p.warning = std::move(w);
  p.record = std::move(r);
  return p;
}
}  // namespace de4sdv::score_interface

struct Rig {
  fakes::CommandSink* command = nullptr;
  fakes::WarningSink* warning = nullptr;
  fakes::RecordSource* record = nullptr;
  fakes::SimulatorClient* client = nullptr;
  std::unique_ptr<si::ScoreInterface> module;
};

static Rig MakeRig(const std::string& log_path = "") {
  Rig rig;
  si::MwComPorts ports;
  auto c = std::make_unique<fakes::CommandSink>();
  auto w = std::make_unique<fakes::WarningSink>();
  auto r = std::make_unique<fakes::RecordSource>();
  auto client = std::make_unique<fakes::SimulatorClient>();
  rig.command = c.get();
  rig.warning = w.get();
  rig.record = r.get();
  rig.client = client.get();
  ports.command = std::move(c);
  ports.warning = std::move(w);
  ports.record = std::move(r);
  si::Settings settings;
  settings.log_path = log_path;
  std::string error;
  rig.module = si::ScoreInterface::Start(settings, std::move(ports), std::move(client), &error);
  return rig;
}

static Plan MakePlan(double acceleration, std::vector<Warning> warnings) {
  return Plan{acceleration, {0.0, 0.02, 0.03}, std::move(warnings)};
}

static std::vector<std::string> Lines(const std::string& path) {
  std::vector<std::string> out;
  std::ifstream f(path);
  for (std::string l; std::getline(f, l);) out.push_back(l);
  return out;
}

static std::uint32_t Bits(float f) {
  std::uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}

static void TestCameraHandsOnNewestAndCountsDrops(const std::string& dir) {
  const std::string log_path = dir + "/camera_test.jsonl";
  Rig rig = MakeRig(log_path);
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  EXPECT(rig.client->attached && rig.client->started);
  auto camera = rig.module->camera();
  EXPECT(camera->is_device_open());
  EXPECT(camera->get_latest_frame().empty());  // nothing yet

  rig.client->Deliver(10, 0.50, 6, 4);
  rig.client->Deliver(12, 0.60, 6, 4);
  rig.client->Deliver(14, 0.70, 6, 4);
  cv::Mat frame = camera->get_latest_frame();
  EXPECT(!frame.empty());
  EXPECT(frame.type() == CV_8UC3);
  EXPECT(frame.cols == 6 && frame.rows == 4);
  if (!frame.empty() && frame.type() == CV_8UC3) {
    const cv::Vec3b px = frame.at<cv::Vec3b>(3, 5);  // row y = 3, column x = 5
    EXPECT(px[0] == 5 && px[1] == 3 && px[2] == 14);  // B, G, R of the newest image (frame 14)
  }
  const CameraStats stats = camera->get_camera_stats();
  EXPECT(stats.frames_received == 3);
  EXPECT(stats.frames_dropped == 2);
  EXPECT(stats.frames_captured == 1);
  EXPECT(stats.current_width == 6 && stats.current_height == 4);
  EXPECT(camera->get_latest_frame().empty());  // handed on once

  rig.client->Deliver(16, 0.80, 6, 4);
  EXPECT(!camera->get_latest_frame().empty());
  EXPECT(camera->get_camera_stats().frames_dropped == 2);
  rig.module.reset();

  int dropped_lines = 0;
  bool frame10 = false, frame12 = false, summary = false;
  for (const auto& l : Lines(log_path)) {
    if (l.find("\"kind\":\"drop.camera_image\"") != std::string::npos) {
      ++dropped_lines;
      frame10 = frame10 || l.find("\"frame\":10,") != std::string::npos;
      frame12 = frame12 || l.find("\"frame\":12,") != std::string::npos;
    }
    if (l.find("\"kind\":\"summary\"") != std::string::npos)
      summary = l.find("\"images_dropped\":2,") != std::string::npos;
  }
  EXPECT(dropped_lines == 2 && frame10 && frame12);  // each dropped image is named
  EXPECT(summary);
  std::remove(log_path.c_str());
}

static void TestRigSizedImage() {
  Rig rig = MakeRig();
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  rig.client->Deliver(2, 0.1, 1920, 1280);  // the rig's size (MAP-DRIVING-DA-CAMERA-IMAGE)
  cv::Mat frame = rig.module->camera()->get_latest_frame();
  EXPECT(frame.cols == 1920 && frame.rows == 1280 && frame.type() == CV_8UC3);
  if (!frame.empty()) {
    const cv::Vec3b px = frame.at<cv::Vec3b>(1279, 1919);
    EXPECT(px[0] == static_cast<std::uint8_t>(1919) && px[1] == static_cast<std::uint8_t>(1279) && px[2] == 2);
  }
}

static void TestCaptureTimeCarriedPerPass() {
  Rig rig = MakeRig();
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  auto camera = rig.module->camera();
  auto vehicle = rig.module->vehicle();
  rig.record->pending.push_back(fakes::GoodRecord());

  rig.client->Deliver(21, 1.05, 4, 2);
  EXPECT(!camera->get_latest_frame().empty());
  vehicle->write(0.1, -4.0);
  rig.module->warning_request_publisher().Publish(MakePlan(-4.0, {Warning::FCW}));

  rig.client->Deliver(23, 1.15, 4, 2);
  rig.client->Deliver(25, 1.25, 4, 2);  // replaces frame 23 unread
  EXPECT(!camera->get_latest_frame().empty());
  vehicle->write(-0.05, -5.5);
  rig.module->warning_request_publisher().Publish(MakePlan(-5.5, {Warning::AEB}));

  EXPECT(camera->get_latest_frame().empty());  // a pass without a new image: no command in the loop either

  // An image that arrives while the pass runs (during the inference) does not change the pass's capture time.
  rig.client->Deliver(27, 1.35, 4, 2);
  EXPECT(!camera->get_latest_frame().empty());
  rig.client->Deliver(29, 1.45, 4, 2);
  vehicle->write(0.0, -1.0);
  rig.module->warning_request_publisher().Publish(MakePlan(-1.0, {}));

  EXPECT(rig.command->sent.size() == 3);
  if (rig.command->sent.size() == 3) {
    EXPECT(rig.command->sent[0].issueTime == 1.05);
    EXPECT(rig.command->sent[1].issueTime == 1.25);  // the image handed on in this pass, not the dropped one
    EXPECT(rig.command->sent[2].issueTime == 1.35);  // not 1.45, which arrived during the pass
    EXPECT(rig.command->sent[0].sequenceCount == 1u && rig.command->sent[1].sequenceCount == 2u);
    EXPECT(rig.command->sent[2].sequenceCount == 3u);
    EXPECT(Bits(rig.command->sent[0].steeringAngle) == 0xc0b758b4u);  // Python: struct.pack('<f', -0.1*180/pi)
    EXPECT(Bits(rig.command->sent[1].steeringAngle) == 0x403758b4u);  // Python: struct.pack('<f', 0.05*180/pi)
    EXPECT(rig.command->sent[0].acceleration == -4.0f && rig.command->sent[1].acceleration == -5.5f);
    for (const auto& p : rig.command->sent) EXPECT(p.checkValue == da::DrivingCommandCheckValue(p));
  }
  EXPECT(rig.warning->sent.size() == 3);
  if (rig.warning->sent.size() == 3) {
    const std::uint8_t w0[8] = {0, 0, 0, 1, 0, 0, 0x04, 0x1a};  // requested, 1050 ms
    const std::uint8_t w1[8] = {0, 0, 0, 1, 0, 0, 0x04, 0xe2};  // requested, 1250 ms
    const std::uint8_t w2[8] = {0, 0, 0, 0, 0, 0, 0x05, 0x46};  // not requested, 1350 ms
    EXPECT(std::memcmp(rig.warning->sent[0].data(), w0, 8) == 0);
    EXPECT(std::memcmp(rig.warning->sent[1].data(), w1, 8) == 0);
    EXPECT(std::memcmp(rig.warning->sent[2].data(), w2, 8) == 0);
  }
}

static void TestNoCommandBeforeRecordThroughVehicleInterface() {
  Rig rig = MakeRig();
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  auto camera = rig.module->camera();
  auto vehicle = rig.module->vehicle();
  for (int i = 0; i < 3; ++i) {
    rig.client->Deliver(static_cast<std::uint64_t>(2 * i), 0.1 * i, 4, 2);
    camera->get_latest_frame();
    vehicle->write(0.0, -1.0);
    rig.module->warning_request_publisher().Publish(MakePlan(-1.0, {}));
  }
  EXPECT(rig.command->sent.empty());
  EXPECT(rig.warning->sent.size() == 3);  // the warning request is not gated by the record
  rig.record->pending.push_back(fakes::GoodRecord());
  rig.client->Deliver(6, 0.3, 4, 2);
  camera->get_latest_frame();
  vehicle->write(0.0, -1.0);
  EXPECT(rig.command->sent.size() == 1);
  EXPECT(!rig.command->sent.empty() && rig.command->sent[0].sequenceCount == 1u);
  EXPECT(rig.module->Summary().find("\"commands_withheld_before_record\":3,") != std::string::npos);
}

static void TestOneWarningEventPerPlan() {
  Rig rig = MakeRig();
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  rig.client->Deliver(2, 0.1, 4, 2);
  rig.module->camera()->get_latest_frame();
  struct Case {
    std::vector<Warning> warnings;
    bool requested;
  };
  const std::vector<Case> cases = {
      {{}, false},
      {{Warning::None}, false},
      {{Warning::LLDW}, false},
      {{Warning::RLDW}, false},
      {{Warning::FCW}, true},
      {{Warning::AEB}, true},
      {{Warning::LLDW, Warning::FCW}, true},
      {{Warning::RLDW, Warning::AEB}, true},
      {{Warning::LLDW}, false},
  };
  for (std::size_t i = 0; i < cases.size(); ++i) {
    EXPECT(si::HoldsForwardCollisionWarningOrEmergencyBraking(cases[i].warnings) == cases[i].requested);
    rig.module->warning_request_publisher().Publish(MakePlan(-1.0, cases[i].warnings));
    EXPECT(rig.warning->sent.size() == i + 1);  // exactly one event per plan
    if (rig.warning->sent.size() == i + 1) EXPECT(rig.warning->sent[i][3] == (cases[i].requested ? 1 : 0));
  }
}

static void TestReadGivesSpeedInMetersPerSecond() {
  Rig rig = MakeRig();
  EXPECT(rig.module != nullptr);
  if (!rig.module) return;
  auto vehicle = rig.module->vehicle();
  EXPECT(vehicle->read() == 0.0);  // no snapshot yet
  EXPECT(vehicle->speed_unavailable() == 1);
  rig.client->has_velocity = true;
  rig.client->velocity = {40, 2.0, 3.0, -4.0, 0.0};
  EXPECT(vehicle->read() == 5.0);
  rig.client->velocity = {42, 2.1, 16.0 / 3.6, 0.0, 0.0};  // 16 km/h
  EXPECT(std::fabs(vehicle->read() - 4.444444444444445) < 1e-12);
}

static void TestStartReadsSettingsAndUsesFactories(const std::string& dir) {
  const std::string conf = dir + "/de4sdv_score_interface_test.conf";
  {
    std::ofstream f(conf);
    f << "mw_com.config = /opt/de4sdv/etc/mw_com_config.json\ncarla.host = 192.0.2.10\ncarla.hero_role = hero\n"
         "carla.camera_role = front_camera_test\n";
  }
  setenv(si::kSettingsPathVariable, conf.c_str(), 1);
  auto module = si::ScoreInterface::Start();
  EXPECT(module != nullptr);
  EXPECT(g_mw_com_config == "/opt/de4sdv/etc/mw_com_config.json");
  EXPECT(g_carla.host == "192.0.2.10" && g_carla.camera_role == "front_camera_test" && g_carla.port == 2000);
  EXPECT(g_client != nullptr && g_client->started);
  module.reset();
  setenv(si::kSettingsPathVariable, (dir + "/no_such.conf").c_str(), 1);
  EXPECT(si::ScoreInterface::Start() == nullptr);
  unsetenv(si::kSettingsPathVariable);
  std::remove(conf.c_str());
}

int main() {
  const char* tmp = std::getenv("TMPDIR");
  const std::string dir = tmp != nullptr ? tmp : ".";
  TestCameraHandsOnNewestAndCountsDrops(dir);
  TestRigSizedImage();
  TestCaptureTimeCarriedPerPass();
  TestNoCommandBeforeRecordThroughVehicleInterface();
  TestOneWarningEventPerPlan();
  TestReadGivesSpeedInMetersPerSecond();
  TestStartReadsSettingsAndUsesFactories(dir);
  if (failures != 0) {
    std::printf("adapters_test: %d failed\n", failures);
    return 1;
  }
  std::printf("adapters_test: all passed\n");
  return 0;
}
