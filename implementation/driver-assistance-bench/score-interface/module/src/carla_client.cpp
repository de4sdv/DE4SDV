// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The CARLA 1.0 client behind seams.hpp (MakeCarlaClient), the one C++20 unit of the module: the client library of
// CARLA 1.0 builds as C++20, so the readiness probe of 2026-11-15 compiled only the unit that calls it as C++20 and
// the rest of the process as C++17. NOT COMPILED on the DE4SDV host: it needs the CARLA 1.0 client headers and
// libraries, which only the S-CORE Bazel build (brief item B2) provides. The calls follow that probe's client unit
// and the closed-loop driving bench's CARLA source.
//
// The world side spawns the hero and its front camera and ticks the world. This client only reads: it never spawns,
// ticks, sets settings or controls anything (the actuation adapter applies the control).
#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include <carla/client/Actor.h>
#include <carla/client/ActorList.h>
#include <carla/client/Client.h>
#include <carla/client/Sensor.h>
#include <carla/client/World.h>
#include <carla/client/WorldSnapshot.h>
#include <carla/sensor/data/Image.h>

#include "de4sdv/score_interface/seams.hpp"

namespace de4sdv::score_interface {

namespace {

namespace cc = carla::client;

std::string RoleOf(const cc::Actor& actor) {
  for (const auto& attribute : actor.GetAttributes()) {
    if (attribute.GetId() == "role_name") return attribute.GetValue();
  }
  return {};
}

class CarlaClient : public SimulatorClient {
 public:
  explicit CarlaClient(CarlaSettings settings) : settings_(std::move(settings)) {}
  ~CarlaClient() override { Stop(); }

  bool Attach(std::string* error) override {
    try {
      client_ = std::make_unique<cc::Client>(settings_.host, static_cast<std::uint16_t>(settings_.port));
      client_->SetTimeout(std::chrono::milliseconds(static_cast<long>(settings_.timeout_s * 1000.0)));
      world_ = std::make_unique<cc::World>(client_->GetWorld());
      const auto deadline = std::chrono::steady_clock::now() +
                            std::chrono::milliseconds(static_cast<long>(settings_.attach_timeout_s * 1000.0));
      for (;;) {
        carla::SharedPtr<cc::Actor> hero;
        carla::SharedPtr<cc::Actor> camera;
        const auto actors = world_->GetActors();
        for (auto it = actors->begin(); it != actors->end(); ++it) {
          const carla::SharedPtr<cc::Actor> actor = *it;
          const std::string role = RoleOf(*actor);
          if (role == settings_.hero_role && actor->GetTypeId().rfind("vehicle.", 0) == 0) hero = actor;
          if (role == settings_.camera_role && actor->GetTypeId() == "sensor.camera.rgb") camera = actor;
        }
        if (hero && camera) {
          if (camera->GetParent() == nullptr || camera->GetParent()->GetId() != hero->GetId()) {
            *error = "the camera '" + settings_.camera_role + "' is not attached to the hero";
            return false;
          }
          hero_id_ = hero->GetId();
          camera_ = std::static_pointer_cast<cc::Sensor>(camera);
          return true;
        }
        if (std::chrono::steady_clock::now() >= deadline) {
          *error = "no hero '" + settings_.hero_role + "' with a camera '" + settings_.camera_role + "'";
          return false;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
      }
    } catch (const std::exception& e) {
      *error = std::string("CARLA client: ") + e.what();
      return false;
    }
  }

  bool Start(ImageHandler on_image, std::string* error) override {
    if (!camera_) {
      *error = "Start before Attach";
      return false;
    }
    handler_ = std::move(on_image);
    running_.store(true);
    try {
      camera_->Listen([this](auto data) {
        if (!running_.load()) return;
        const auto image = std::static_pointer_cast<carla::sensor::data::Image>(data);
        CameraImageView view;
        view.frame = image->GetFrame();
        view.sim_time_s = image->GetTimestamp();  // simulation s of the world snapshot the image was rendered in
        view.width = static_cast<int>(image->GetWidth());
        view.height = static_cast<int>(image->GetHeight());
        view.row_bytes = static_cast<std::size_t>(image->GetWidth()) * sizeof(carla::sensor::data::Color);
        view.bgra = reinterpret_cast<const std::uint8_t*>(image->data());  // Color is b, g, r, a
        handler_(view);
      });
    } catch (const std::exception& e) {
      *error = std::string("CARLA client: ") + e.what();
      return false;
    }
    return true;
  }

  bool NewestEgoVelocity(EgoVelocity* out) override {
    if (!world_) return false;
    try {
      const cc::WorldSnapshot snapshot = world_->GetSnapshot();  // the newest snapshot the client holds
      const auto hero = snapshot.Find(hero_id_);
      if (!hero) return false;
      out->frame = snapshot.GetFrame();
      out->sim_time_s = snapshot.GetTimestamp().elapsed_seconds;
      out->x = hero->velocity.x;
      out->y = hero->velocity.y;
      out->z = hero->velocity.z;
      return true;
    } catch (const std::exception&) {
      return false;
    }
  }

  void Stop() override {
    running_.store(false);
    try {
      if (camera_ && camera_->IsListening()) camera_->Stop();
    } catch (const std::exception&) {
      // the server may be gone at shutdown
    }
  }

 private:
  CarlaSettings settings_;
  std::unique_ptr<cc::Client> client_;
  std::unique_ptr<cc::World> world_;
  carla::SharedPtr<cc::Sensor> camera_;
  carla::ActorId hero_id_ = 0;
  ImageHandler handler_;
  std::atomic<bool> running_{false};
};

}  // namespace

std::unique_ptr<SimulatorClient> MakeCarlaClient(const CarlaSettings& settings) {
  return std::make_unique<CarlaClient>(settings);
}

}  // namespace de4sdv::score_interface
