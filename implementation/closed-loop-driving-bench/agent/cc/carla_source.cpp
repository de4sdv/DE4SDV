#include "carla_source.h"

#include <atomic>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>

#include <carla/client/Actor.h>
#include <carla/client/ActorList.h>
#include <carla/client/Client.h>
#include <carla/client/Sensor.h>
#include <carla/client/Vehicle.h>
#include <carla/client/World.h>
#include <carla/client/WorldSnapshot.h>
#include <carla/rpc/VehiclePhysicsControl.h>
#include <carla/sensor/data/Image.h>

#include "ego_motion.h"

namespace de4sdv::driving::agent {

namespace cc = carla::client;
namespace cg = carla::geom;

namespace {

std::int64_t MonoNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

std::string RoleOf(const cc::Actor& actor) {
  for (const auto& attribute : actor.GetAttributes()) {
    if (attribute.GetId() == "role_name") return attribute.GetValue();
  }
  return {};
}

std::string AttributeOf(const cc::Actor& actor, const std::string& id) {
  for (const auto& attribute : actor.GetAttributes()) {
    if (attribute.GetId() == id) return attribute.GetValue();
  }
  return {};
}

// UE local -> world, row-major, from the transform's Euler angles (CarlaAxes: GetMatrix's columns).
std::array<double, 16> MatrixOf(const cg::Transform& t) {
  double f[3], r[3], u[3];
  CarlaAxes(t.rotation.pitch, t.rotation.yaw, t.rotation.roll, f, r, u);
  return {f[0], r[0], u[0], t.location.x, f[1], r[1], u[1], t.location.y,
          f[2], r[2], u[2], t.location.z, 0.0,  0.0,  0.0,  1.0};
}

void Json16(std::ostringstream& os, const std::array<double, 16>& m) {
  os << "[";
  for (int i = 0; i < 16; ++i) os << (i ? "," : "") << std::setprecision(17) << m[i];
  os << "]";
}

CarlaKinematics KinematicsOf(const cc::ActorSnapshot& s) {
  CarlaKinematics k;
  k.x = s.transform.location.x;
  k.y = s.transform.location.y;
  k.z = s.transform.location.z;
  k.roll = s.transform.rotation.roll;
  k.pitch = s.transform.rotation.pitch;
  k.yaw = s.transform.rotation.yaw;
  k.vx = s.velocity.x;
  k.vy = s.velocity.y;
  k.vz = s.velocity.z;
  k.ax = s.acceleration.x;
  k.ay = s.acceleration.y;
  k.az = s.acceleration.z;
  k.wx = s.angular_velocity.x;  // deg/s
  k.wy = s.angular_velocity.y;
  k.wz = s.angular_velocity.z;
  return k;
}

}  // namespace

struct CarlaSource::Impl {
  CarlaSourceConfig config;
  std::unique_ptr<cc::Client> client;
  std::unique_ptr<cc::World> world;
  carla::SharedPtr<cc::Actor> hero;
  std::array<carla::SharedPtr<cc::Sensor>, kCameraCount> cameras{};
  std::array<CarlaCameraInfo, kCameraCount> info{};
  std::string server_version;
  FrameStore* store = nullptr;
  std::size_t tick_callback = 0;
  bool tick_registered = false;
  std::atomic<bool> running{false};
  std::thread sweep;
  std::atomic<std::uint64_t> ticks{0};
  std::atomic<std::uint64_t> ticks_without_hero{0};
  std::array<std::atomic<std::uint64_t>, kCameraCount> images{};
};

CarlaSource::CarlaSource() : impl_(std::make_unique<Impl>()) {}
CarlaSource::~CarlaSource() { Stop(); }

const CarlaCameraInfo& CarlaSource::camera(std::size_t index) const { return impl_->info.at(index); }
const std::string& CarlaSource::server_version() const { return impl_->server_version; }
std::uint64_t CarlaSource::ticks() const { return impl_->ticks.load(); }
std::uint64_t CarlaSource::images(std::size_t index) const { return impl_->images.at(index).load(); }
std::uint64_t CarlaSource::ticks_without_hero() const { return impl_->ticks_without_hero.load(); }

bool CarlaSource::Attach(const CarlaSourceConfig& config, std::string* rig_json, std::string* info_json,
                         std::string* error) {
  Impl& m = *impl_;
  m.config = config;
  const auto t_attach = std::chrono::steady_clock::now();
  try {
    m.client = std::make_unique<cc::Client>(config.host, static_cast<std::uint16_t>(config.port));
    m.client->SetTimeout(std::chrono::milliseconds(static_cast<long>(config.rpc_timeout_s * 1000.0)));
    m.server_version = m.client->GetServerVersion();
    m.world = std::make_unique<cc::World>(m.client->GetWorld());

    // 1. Wait for the hero and the six cameras.
    int polls = 0;
    for (;;) {
      ++polls;
      m.hero = nullptr;
      for (auto& c : m.cameras) c = nullptr;
      const auto actors = m.world->GetActors();
      for (auto it = actors->begin(); it != actors->end(); ++it) {
        const carla::SharedPtr<cc::Actor> actor = *it;
        const std::string role = RoleOf(*actor);
        if (role == config.hero_role && actor->GetTypeId().rfind("vehicle.", 0) == 0) m.hero = actor;
        for (std::size_t i = 0; i < kCameraCount; ++i) {
          if (role == config.camera_roles[i] && actor->GetTypeId() == "sensor.camera.rgb") {
            m.cameras[i] = boost::static_pointer_cast<cc::Sensor>(actor);
          }
        }
      }
      bool all = m.hero != nullptr;
      for (const auto& c : m.cameras) all = all && c != nullptr;
      if (all) break;
      if (std::chrono::duration<double>(std::chrono::steady_clock::now() - t_attach).count() > config.attach_timeout_s) {
        std::ostringstream os;
        os << "no hero '" << config.hero_role << "' with six cameras after " << config.attach_timeout_s
           << " s (hero " << (m.hero ? "found" : "missing") << "; cameras missing:";
        for (std::size_t i = 0; i < kCameraCount; ++i) {
          if (!m.cameras[i]) os << " " << config.camera_roles[i];
        }
        os << ")";
        *error = os.str();
        return false;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }
    for (std::size_t i = 0; i < kCameraCount; ++i) {
      CarlaCameraInfo& ci = m.info[i];
      ci.actor_id = m.cameras[i]->GetId();
      ci.width = std::stoi(AttributeOf(*m.cameras[i], "image_size_x"));
      ci.height = std::stoi(AttributeOf(*m.cameras[i], "image_size_y"));
      ci.fov = std::stod(AttributeOf(*m.cameras[i], "fov"));
      if (m.cameras[i]->GetParentId() != m.hero->GetId()) {
        *error = config.camera_roles[i] + " is not attached to the hero";
        return false;
      }
    }

    // 2. The rig, from one world frame: the wheel positions come from an RPC, so the read counts
    //    only if the client saw no newer tick while it ran and the RPC returned well inside a tick.
    const auto vehicle = boost::static_pointer_cast<cc::Vehicle>(m.hero);
    for (int attempt = 1; attempt <= 20; ++attempt) {
      const cc::WorldSnapshot before = m.world->WaitForTick(std::chrono::seconds(5));
      const auto t0 = std::chrono::steady_clock::now();
      const auto physics = vehicle->GetPhysicsControl();
      const double rpc_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
      const cc::WorldSnapshot after = m.world->GetSnapshot();
      if (after.GetFrame() != before.GetFrame() || rpc_ms > 50.0) continue;
      const auto hero_snap = before.Find(m.hero->GetId());
      if (!hero_snap) continue;
      const auto& wheels = physics.GetWheels();
      if (wheels.size() != 4) {
        *error = "the hero has " + std::to_string(wheels.size()) + " wheels, the rig needs 4";
        return false;
      }
      std::ostringstream rig;
      rig << "{\"vehicle\":{\"world_matrix\":";
      Json16(rig, MatrixOf(hero_snap->transform));
      rig << ",\"location\":[" << std::setprecision(17) << hero_snap->transform.location.x << ","
          << hero_snap->transform.location.y << "," << hero_snap->transform.location.z << "],\"wheel_positions\":[";
      for (std::size_t w = 0; w < 4; ++w) {
        rig << (w ? "," : "") << "[" << wheels[w].position.x << "," << wheels[w].position.y << ","
            << wheels[w].position.z << "]";
      }
      rig << "],\"wheel_radii\":[";
      for (std::size_t w = 0; w < 4; ++w) rig << (w ? "," : "") << wheels[w].radius;
      rig << "]},\"cameras\":[";
      for (std::size_t i = 0; i < kCameraCount; ++i) {
        const auto cam_snap = before.Find(m.info[i].actor_id);
        if (!cam_snap) {
          *error = config.camera_roles[i] + " is not in the world snapshot";
          return false;
        }
        rig << (i ? "," : "") << "{\"role\":\"" << config.camera_roles[i] << "\",\"width\":" << m.info[i].width
            << ",\"height\":" << m.info[i].height << ",\"fov\":" << m.info[i].fov << ",\"world_matrix\":";
        Json16(rig, MatrixOf(cam_snap->transform));
        rig << "}";
      }
      rig << "]}";
      *rig_json = rig.str();
      std::ostringstream info;
      info << "{\"host\":\"" << config.host << "\",\"port\":" << config.port << ",\"serverVersion\":\"" << m.server_version << "\"" << ",\"heroId\":" << m.hero->GetId()
           << ",\"heroType\":\"" << m.hero->GetTypeId() << "\",\"cameras\":[";
      for (std::size_t i = 0; i < kCameraCount; ++i) {
        info << (i ? "," : "") << "{\"role\":\"" << config.camera_roles[i] << "\",\"actorId\":" << m.info[i].actor_id
             << ",\"width\":" << m.info[i].width << ",\"height\":" << m.info[i].height << ",\"fov\":" << m.info[i].fov
             << "}";
      }
      info << "],\"rigFrame\":" << before.GetFrame() << ",\"rigAttempts\":" << attempt
           << ",\"physicsRpcMs\":" << rpc_ms << ",\"polls\":" << polls << ",\"attachSeconds\":"
           << std::chrono::duration<double>(std::chrono::steady_clock::now() - t_attach).count() << "}";
      *info_json = info.str();
      return true;
    }
    *error = "no rig read inside one world frame in 20 attempts";
    return false;
  } catch (const std::exception& e) {
    *error = std::string("LibCarla: ") + e.what();
    return false;
  }
}

bool CarlaSource::Start(FrameStore* store, std::string* error) {
  Impl& m = *impl_;
  if (m.world == nullptr || m.hero == nullptr) {
    *error = "Start before Attach";
    return false;
  }
  m.store = store;
  m.running = true;
  try {
    for (std::size_t i = 0; i < kCameraCount; ++i) {
      m.cameras[i]->Listen([this, i](carla::SharedPtr<carla::sensor::SensorData> data) {
        const std::int64_t arrival = MonoNs();
        const auto image = boost::static_pointer_cast<carla::sensor::data::Image>(data);
        if (impl_->store == nullptr || !impl_->running.load()) return;
        impl_->store->OnImage(i, image->GetFrame(), reinterpret_cast<const std::uint8_t*>(image->data()),
                              image->size() * sizeof(carla::sensor::data::Color), static_cast<int>(image->GetWidth()),
                              static_cast<int>(image->GetHeight()), static_cast<double>(image->GetFOVAngle()), arrival);
        impl_->images[i].fetch_add(1);
      });
    }
    const auto hero_id = m.hero->GetId();
    m.tick_callback = m.world->OnTick([this, hero_id](cc::WorldSnapshot ws) {
      const std::int64_t arrival = MonoNs();
      if (impl_->store == nullptr || !impl_->running.load()) return;
      const auto s = ws.Find(hero_id);
      if (!s) {
        impl_->ticks_without_hero.fetch_add(1);
        return;
      }
      impl_->store->OnSnapshot(ws.GetFrame(), SnapshotFromCarla(KinematicsOf(*s)), arrival);
      impl_->ticks.fetch_add(1);
    });
    m.tick_registered = true;
  } catch (const std::exception& e) {
    *error = std::string("LibCarla: ") + e.what();
    return false;
  }
  m.sweep = std::thread([this] {
    while (impl_->running.load()) {
      impl_->store->PollDeadlines(MonoNs());
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
  });
  return true;
}

void CarlaSource::Stop() {
  Impl& m = *impl_;
  const bool was_running = m.running.exchange(false);
  try {
    if (m.tick_registered && m.world) {
      m.world->RemoveOnTick(m.tick_callback);
      m.tick_registered = false;
    }
    for (auto& c : m.cameras) {
      if (c && c->IsListening()) c->Stop();
    }
  } catch (const std::exception&) {
    // the server may be gone at shutdown; nothing to release on our side
  }
  if (m.sweep.joinable()) m.sweep.join();
  (void)was_running;
}

}  // namespace de4sdv::driving::agent
