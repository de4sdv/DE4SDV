// DE4SDV vehicle-speed provider of the S-CORE reference interoperability
// bench (INC-MW-011): an S-CORE application outside the system of interest
// that offers the reference vehicle speed as an mw::com event (phase-8 port
// referenceSpeedOut of vehicleSpeedProvider).
//
// It sends the values of --values in order, one every --period-ms, and starts
// again at the first value until --count samples are sent (0: until SIGTERM).
// Values may be nan, inf and -inf, so a run can exercise REQ-MW-011. Each
// sent sample is logged as one JSON line with its sequence number, the value
// and its IEEE-754 bits, CLOCK_MONOTONIC and CLOCK_REALTIME in nanoseconds
// and the send result. Test and bench use only; it reads no vehicle signal.

#include <getopt.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cinttypes>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "de4sdv_score_interface/reference_vehicle_speed_service.h"
#include "score/filesystem/path.h"
#include "score/mw/com/runtime.h"

namespace {

std::atomic<bool> g_stop{false};

void OnSignal(int /*signal*/) { g_stop.store(true); }

std::int64_t ClockNs(clockid_t clock) {
  timespec ts{};
  clock_gettime(clock, &ts);
  return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

bool ParseValue(const std::string& text, double* value) {
  if (text == "nan") {
    *value = std::nan("");
    return true;
  }
  if (text == "inf" || text == "+inf") {
    *value = HUGE_VAL;
    return true;
  }
  if (text == "-inf") {
    *value = -HUGE_VAL;
    return true;
  }
  char* end = nullptr;
  errno = 0;
  const double parsed = std::strtod(text.c_str(), &end);
  if (errno != 0 || end == text.c_str() || *end != '\0' || !std::isfinite(parsed)) {
    return false;
  }
  *value = parsed;
  return true;
}

bool ParseValues(const std::string& list, std::vector<double>* values) {
  std::size_t start = 0;
  while (start <= list.size()) {
    const std::size_t comma = list.find(',', start);
    const std::string item = list.substr(start, comma == std::string::npos ? std::string::npos : comma - start);
    double value = 0.0;
    if (!ParseValue(item, &value)) {
      return false;
    }
    values->push_back(value);
    if (comma == std::string::npos) {
      break;
    }
    start = comma + 1;
  }
  return !values->empty();
}

std::string ValueText(double value) {
  if (std::isnan(value)) {
    return "\"nan\"";
  }
  if (std::isinf(value)) {
    return value > 0 ? "\"inf\"" : "\"-inf\"";
  }
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%.17g", value);
  return buffer;
}

std::uint64_t Bits(double value) {
  std::uint64_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

void PrintHelp() {
  std::printf(
      "vehicle_speed_provider --service_instance_manifest <mw_com_config.json> --values <v1,v2,...>\n"
      "  [--period-ms <ms, default 100>] [--count <n, 0 = until SIGTERM>] [--log <jsonl path>]\n"
      "  values: decimal numbers in km/h, or nan, inf, -inf\n");
}

}  // namespace

int main(int argc, char* argv[]) {
  std::signal(SIGTERM, OnSignal);
  std::signal(SIGINT, OnSignal);

  std::string manifest;
  std::string values_text;
  std::string log_path;
  long period_ms = 100;
  long long count = 0;

  const option long_options[] = {{"service_instance_manifest", required_argument, nullptr, 's'},
                                 {"values", required_argument, nullptr, 'v'},
                                 {"period-ms", required_argument, nullptr, 'p'},
                                 {"count", required_argument, nullptr, 'n'},
                                 {"log", required_argument, nullptr, 'l'},
                                 {"help", no_argument, nullptr, 'h'},
                                 {nullptr, no_argument, nullptr, 0}};
  while (true) {
    const int option = getopt_long(argc, argv, "s:v:p:n:l:h", long_options, nullptr);
    if (option == -1) {
      break;
    }
    switch (option) {
      case 's':
        manifest = optarg;
        break;
      case 'v':
        values_text = optarg;
        break;
      case 'p':
        period_ms = std::strtol(optarg, nullptr, 10);
        break;
      case 'n':
        count = std::strtoll(optarg, nullptr, 10);
        break;
      case 'l':
        log_path = optarg;
        break;
      case 'h':
        PrintHelp();
        return 0;
      default:
        PrintHelp();
        return 1;
    }
  }
  std::vector<double> values;
  if (manifest.empty() || !ParseValues(values_text, &values) || period_ms <= 0 || count < 0) {
    PrintHelp();
    return 1;
  }
  std::FILE* log = nullptr;
  if (!log_path.empty()) {
    log = std::fopen(log_path.c_str(), "a");
    if (log == nullptr) {
      std::fprintf(stderr, "cannot open %s\n", log_path.c_str());
      return 1;
    }
  }

  score::mw::com::runtime::InitializeRuntime(
      score::mw::com::runtime::RuntimeConfiguration{score::filesystem::Path{manifest}});
  auto specifier = score::mw::com::InstanceSpecifier::Create(
      std::string{de4sdv::score_interface::kReferenceVehicleSpeedInstanceSpecifier});
  if (!specifier.has_value()) {
    std::fprintf(stderr, "instance specifier: %s\n", std::string{specifier.error().Message()}.c_str());
    return 2;
  }
  auto created = de4sdv::score_interface::ReferenceVehicleSpeedSkeleton::Create(specifier.value());
  if (!created.has_value()) {
    std::fprintf(stderr, "skeleton create: %s\n", std::string{created.error().Message()}.c_str());
    return 3;
  }
  auto skeleton = std::move(created).value();
  const auto offered = skeleton.OfferService();
  if (!offered.has_value()) {
    std::fprintf(stderr, "offer: %s\n", std::string{offered.error().Message()}.c_str());
    return 4;
  }
  std::printf("{\"event\":\"offered\",\"pid\":%d,\"monotonic_ns\":%" PRId64 "}\n", static_cast<int>(getpid()),
              ClockNs(CLOCK_MONOTONIC));
  std::fflush(stdout);
  if (log != nullptr) {
    std::fprintf(log, "{\"event\":\"offered\",\"pid\":%d,\"monotonic_ns\":%" PRId64 "}\n",
                 static_cast<int>(getpid()), ClockNs(CLOCK_MONOTONIC));
    std::fflush(log);
  }

  const auto period = std::chrono::milliseconds{period_ms};
  auto next = std::chrono::steady_clock::now();
  long long sent = 0;
  std::uint64_t sequence = 0;
  while (!g_stop.load() && (count == 0 || sent < count)) {
    const double value = values[static_cast<std::size_t>(sequence % values.size())];
    ++sequence;
    const std::int64_t monotonic_ns = ClockNs(CLOCK_MONOTONIC);
    const std::int64_t realtime_ns = ClockNs(CLOCK_REALTIME);
    std::string result = "ok";
    auto allocated = skeleton.vehicle_speed_.Allocate();
    if (!allocated.has_value()) {
      result = "allocate_failed";
    } else {
      auto slot = std::move(allocated).value();
      slot->speed_kmh = value;
      const auto send_result = skeleton.vehicle_speed_.Send(std::move(slot));
      if (!send_result.has_value()) {
        result = "send_failed";
      }
    }
    if (log != nullptr) {
      std::fprintf(log,
                   "{\"seq\":%" PRIu64 ",\"speed_kmh\":%s,\"bits\":\"%016" PRIx64 "\",\"monotonic_ns\":%" PRId64
                   ",\"realtime_ns\":%" PRId64 ",\"send\":\"%s\"}\n",
                   sequence, ValueText(value).c_str(), Bits(value), monotonic_ns, realtime_ns, result.c_str());
      std::fflush(log);
    }
    ++sent;
    next += period;
    while (!g_stop.load() && std::chrono::steady_clock::now() < next) {
      std::this_thread::sleep_for(std::min<std::chrono::steady_clock::duration>(
          next - std::chrono::steady_clock::now(), std::chrono::milliseconds{5}));
    }
  }
  skeleton.StopOfferService();
  if (log != nullptr) {
    std::fprintf(log, "{\"event\":\"stopped\",\"sent\":%lld,\"monotonic_ns\":%" PRId64 "}\n", sent,
                 ClockNs(CLOCK_MONOTONIC));
    std::fclose(log);
  }
  std::printf("{\"event\":\"stopped\",\"sent\":%lld}\n", sent);
  return 0;
}
