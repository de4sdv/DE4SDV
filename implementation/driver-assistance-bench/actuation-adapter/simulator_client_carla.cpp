// The actuation adapter's simulator client on CARLA 1.0 (simulator_client.h).
//
// CARLA 1.0's client library at 14ac3b1a50 requires C++20 (its CMake sets
// CMAKE_CXX_STANDARD 20, REQUIRED), so this one translation unit is compiled
// -std=c++20, behind the plain function interface of simulator_client.h; the
// rest of the adapter keeps the S-CORE toolchain's C++17. That split was
// measured to link and run in one S-CORE process by the DA-P8 h probe (owner
// decision h-a, option a).
//
// NOT BUILT ON THIS HOST: it needs LibCarla, which only the B2 S-CORE workspace
// has. The host's tests link tests/fake_simulator_client.cpp instead, and
// tests/test_actuation_adapter_carla_unit.py checks this file's text (no
// autopilot, Ackermann control only, named lists, the C++20 guard).
//
// The DA-P8 h probe ran these calls against a CARLA 1.0 server: Client,
// SetTimeout, GetClientVersion, GetServerVersion, GetWorld, GetSnapshot,
// Timestamp::elapsed_seconds, Vehicle::AckermannControl and
// ApplyAckermannControl, and std::static_pointer_cast on the 1.0 client's
// SharedPtr. Not run by that probe, and so to be shown by the B2 build and
// P10-2: World::OnTick, RemoveOnTick, WorldSnapshot::Find, GetActors,
// ActorList::Filter and Actor::GetAttributes (the closed-loop bench's adapter
// runs them on CARLA 0.9.16). Every signature used here was read, not compiled,
// in the client headers at 14ac3b1a50: Client(host, uint16_t port),
// SetTimeout(time_duration), which converts from std::chrono durations;
// World::OnTick(std::function<void(WorldSnapshot)>) returns the size_t that
// RemoveOnTick takes; WorldSnapshot::Find returns std::optional<ActorSnapshot>,
// which holds the velocity; Vehicle::AckermannControl is
// rpc::VehicleAckermannControl, five floats; ActorAttributeValue::As<std::string>.
//
// Rules from the model (PSR DrivingCommandActuationAdapter): the client takes
// the simulation time and the speed of the ego vehicle from the newest world
// snapshot; it applies the Ackermann control and nothing else; the autopilot of
// the ego vehicle stays off, and this unit never calls SetAutopilot. The world
// is ticked by the world side's pacer, never here.
#if __cplusplus < 202002L
#error "simulator_client_carla.cpp is compiled as C++20 (the CARLA 1.0 client's standard)"
#endif

#include "simulator_client.h"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <utility>

#include <carla/client/ActorList.h>
#include <carla/client/Client.h>
#include <carla/client/Vehicle.h>
#include <carla/client/World.h>
#include <carla/client/WorldSnapshot.h>

namespace de4sdv::driver_assistance::actuation::simulator {
namespace {

namespace cc = carla::client;

struct Session {
  std::unique_ptr<cc::Client> client;
  std::optional<cc::World> world;
  carla::SharedPtr<cc::Vehicle> hero;
  std::optional<std::size_t> callbackId;
};

std::mutex g_mutex;
Session g_session;

bool Fail(std::string* error, const std::string& message) {
  if (error != nullptr) *error = message;
  return false;
}

std::string RoleName(const cc::Actor& actor) {
  for (const auto& attribute : actor.GetAttributes()) {
    if (attribute.GetId() == "role_name") return attribute.As<std::string>();
  }
  return std::string();
}

carla::SharedPtr<cc::Vehicle> FindHero(cc::World& world, const std::string& role) {
  const auto actors = world.GetActors();
  if (!actors) return nullptr;
  // Name the filtered list: a range-for over a dereferenced temporary iterates a
  // list whose only owner is destroyed before the first iteration (the closed-loop
  // bench's adapter aborted with "double free detected in tcache 2" on it).
  const auto vehicles = actors->Filter("vehicle.*");
  if (!vehicles) return nullptr;
  for (const auto& actor : *vehicles) {
    if (RoleName(*actor) == role) return std::static_pointer_cast<cc::Vehicle>(actor);
  }
  return nullptr;
}

double Length(const carla::geom::Vector3D& v) {
  return std::sqrt(static_cast<double>(v.x) * v.x + static_cast<double>(v.y) * v.y +
                   static_cast<double>(v.z) * v.z);
}

}  // namespace

bool Connect(const ClientOptions& options, ClientInfo* info, std::string* error) {
  std::lock_guard<std::mutex> lock(g_mutex);
  try {
    g_session = Session{};
    g_session.client =
        std::make_unique<cc::Client>(options.host, static_cast<std::uint16_t>(options.port));
    g_session.client->SetTimeout(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::duration<double>(options.timeoutS)));
    if (info != nullptr) {
      info->clientVersion = g_session.client->GetClientVersion();
      info->serverVersion = g_session.client->GetServerVersion();
    }
    g_session.world.emplace(g_session.client->GetWorld());
    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::duration_cast<std::chrono::steady_clock::duration>(
                              std::chrono::duration<double>(options.heroWaitS));
    while (!g_session.hero) {
      g_session.hero = FindHero(*g_session.world, options.heroRoleName);
      if (g_session.hero || std::chrono::steady_clock::now() >= deadline) break;
      std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
    if (!g_session.hero) {
      return Fail(error, "no vehicle with role_name " + options.heroRoleName);
    }
    if (info != nullptr) {
      info->heroActorId = g_session.hero->GetId();
      info->heroTypeId = g_session.hero->GetTypeId();
    }
    return true;
  } catch (const std::exception& e) {
    return Fail(error, std::string("CARLA client: ") + e.what());
  }
}

bool StartSnapshots(SnapshotHandler handler, std::string* error) {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (!g_session.world || !g_session.hero) return Fail(error, "not connected");
  try {
    const auto heroId = g_session.hero->GetId();
    g_session.callbackId = g_session.world->OnTick(
        [handler = std::move(handler), heroId](cc::WorldSnapshot snapshot) {
          SnapshotSample sample;
          sample.frame = static_cast<std::uint64_t>(snapshot.GetFrame());
          sample.simTimeS = snapshot.GetTimestamp().elapsed_seconds;
          const auto ego = snapshot.Find(heroId);
          sample.egoPresent = static_cast<bool>(ego);
          sample.speedMps = ego ? Length(ego->velocity) : 0.0;
          handler(sample);
        });
    return true;
  } catch (const std::exception& e) {
    return Fail(error, std::string("CARLA OnTick: ") + e.what());
  }
}

void StopSnapshots() {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (!g_session.world || !g_session.callbackId) return;
  try {
    g_session.world->RemoveOnTick(*g_session.callbackId);
  } catch (const std::exception&) {
    // The server is gone; nothing to remove.
  }
  g_session.callbackId.reset();
}

bool ApplyAckermannControl(const AppliedAckermannControl& control, std::string* error) {
  std::lock_guard<std::mutex> lock(g_mutex);
  if (!g_session.hero) return Fail(error, "not connected");
  cc::Vehicle::AckermannControl ackermann;  // carla::rpc::VehicleAckermannControl, five floats
  ackermann.steer = control.steer;
  ackermann.steer_speed = control.steerSpeed;
  ackermann.speed = control.speed;
  ackermann.acceleration = control.acceleration;
  ackermann.jerk = control.jerk;
  try {
    g_session.hero->ApplyAckermannControl(ackermann);
    return true;
  } catch (const std::exception& e) {
    return Fail(error, e.what());
  }
}

void Disconnect() {
  std::lock_guard<std::mutex> lock(g_mutex);
  g_session = Session{};
}

}  // namespace de4sdv::driver_assistance::actuation::simulator
