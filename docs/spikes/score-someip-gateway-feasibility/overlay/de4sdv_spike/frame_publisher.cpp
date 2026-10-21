// DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
//
// Host-side publisher: an mw::com skeleton that offers the opaque AEBS signal
// frame event and sends one length-prefixed frame of at most 2048 bytes per
// period. It stands in for the adapter of the phase-8 model. Structure follows
// tests/benchmarks/echo_server.cpp of inc_someip_gateway 951fbc09 (skeleton
// Create, OfferService, Allocate, Send of a PreSerializedData sample) and the
// runtime initialisation of score/gatewayd/main.cpp.
//
// Frame layout (opaque to the gateway, interpreted only by the spike's
// analysis): bytes 0..3 big-endian length L of the rest (frame = 4 + L bytes),
// 4..11 big-endian sequence number, 12..19 big-endian CLOCK_MONOTONIC ns at
// build time, 20.. deterministic pseudo-random filler.
//
// Every successfully sent frame is appended to <out>/<tag>_frames.bin as
// (u64 seq, u64 t_ns, u32 len, len bytes), host byte order, so the analysis
// can compare digests with what the guest received. Control is file based so
// the orchestrator can order the scenario steps deterministically.

#include <getopt.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "de4sdv_spike/aebs_signal_frame_service.h"
#include "score/filesystem/path.h"
#include "score/mw/com/runtime.h"

namespace {

std::atomic<bool> g_stop{false};

void OnSignal(int /*signal*/) { g_stop.store(true); }

std::uint64_t NowNs() {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                          std::chrono::steady_clock::now().time_since_epoch())
                                          .count());
}

bool FileExists(const std::string& path) {
    struct stat st {};
    return ::stat(path.c_str(), &st) == 0;
}

void Touch(const std::string& path) {
    FILE* f = std::fopen(path.c_str(), "w");
    if (f != nullptr) {
        std::fclose(f);
    }
}

std::uint64_t SplitMix64(std::uint64_t& state) {
    state += 0x9E3779B97F4A7C15ULL;
    std::uint64_t z = state;
    z = (z ^ (z >> 30U)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27U)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31U);
}

constexpr std::size_t kMinFrameBytes = 20;

std::size_t FrameSize(std::uint64_t seq) {
    switch (seq % 10U) {
        case 1U:
            return de4sdv_spike::kMaxFrameBytes;  // the maximum, 2048
        case 2U:
            return kMinFrameBytes;
        case 3U:
            return 1500U;
        case 4U:
            return 1501U;
        default: {
            std::uint64_t state = seq * 7919U;
            return kMinFrameBytes +
                   static_cast<std::size_t>(SplitMix64(state) %
                                            (de4sdv_spike::kMaxFrameBytes - kMinFrameBytes + 1U));
        }
    }
}

void PutBe(std::vector<std::uint8_t>& out, std::size_t offset, std::uint64_t value, int bytes) {
    for (int i = 0; i < bytes; ++i) {
        out[offset + static_cast<std::size_t>(i)] =
            static_cast<std::uint8_t>(value >> (8 * (bytes - 1 - i)));
    }
}

void BuildFrame(std::uint64_t seq, std::uint64_t t_ns, std::vector<std::uint8_t>& out) {
    const std::size_t total = FrameSize(seq);
    out.assign(total, 0U);
    PutBe(out, 0, static_cast<std::uint64_t>(total - 4U), 4);
    PutBe(out, 4, seq, 8);
    PutBe(out, 12, t_ns, 8);
    std::uint64_t state = seq ^ 0xDE45D7A1C0FFEEULL;
    for (std::size_t i = kMinFrameBytes; i < total; i += 8U) {
        const std::uint64_t v = SplitMix64(state);
        for (std::size_t b = 0; b < 8U && i + b < total; ++b) {
            out[i + b] = static_cast<std::uint8_t>(v >> (8U * b));
        }
    }
}

struct Logs {
    FILE* events{nullptr};
    FILE* frames{nullptr};

    void Event(const std::string& line) const {
        const std::uint64_t now = NowNs();
        if (events != nullptr) {
            std::fprintf(events, "%llu %s\n", static_cast<unsigned long long>(now), line.c_str());
            std::fflush(events);
        }
        std::cout << now << " [frame_publisher] " << line << std::endl;
    }

    void Frame(std::uint64_t seq, std::uint64_t t_ns, const std::vector<std::uint8_t>& bytes) const {
        if (frames == nullptr) {
            return;
        }
        const std::uint32_t len = static_cast<std::uint32_t>(bytes.size());
        std::fwrite(&seq, sizeof(seq), 1, frames);
        std::fwrite(&t_ns, sizeof(t_ns), 1, frames);
        std::fwrite(&len, sizeof(len), 1, frames);
        std::fwrite(bytes.data(), 1, bytes.size(), frames);
        std::fflush(frames);
    }
};

bool WaitForFile(const std::string& path) {
    while (!g_stop.load()) {
        if (FileExists(path)) {
            return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return false;
}

void SleepUntil(std::chrono::steady_clock::time_point deadline) {
    while (!g_stop.load()) {
        const auto now = std::chrono::steady_clock::now();
        if (now >= deadline) {
            return;
        }
        const auto remaining = deadline - now;
        std::this_thread::sleep_for(std::min<std::chrono::steady_clock::duration>(
            remaining, std::chrono::milliseconds(5)));
    }
}

std::set<std::uint64_t> ParseList(const std::string& text) {
    std::set<std::uint64_t> values;
    std::stringstream stream(text);
    std::string item;
    while (std::getline(stream, item, ',')) {
        if (!item.empty()) {
            values.insert(std::strtoull(item.c_str(), nullptr, 10));
        }
    }
    return values;
}

void PrintHelp() {
    std::cout << "frame_publisher --service_instance_manifest <mw_com_config.json> --out <dir>\n"
                 "  [--tag <name>] [--frames <n, 0 = until SIGTERM>] [--period-ms <ms>]\n"
                 "  [--start-seq <seq>] [--pause-at <seq,...>] [--go-file <path>]\n"
                 "  [--linger-s <s>]\n";
}

}  // namespace

int main(int argc, char* argv[]) {
    std::signal(SIGTERM, OnSignal);
    std::signal(SIGINT, OnSignal);

    std::string manifest;
    std::string out_dir;
    std::string tag{"publisher"};
    std::string go_file;
    std::uint64_t frames = 0;
    std::uint64_t period_ms = 50;
    std::uint64_t start_seq = 1;
    std::uint64_t linger_s = 0;
    std::set<std::uint64_t> pause_at;

    const option long_opts[] = {{"service_instance_manifest", required_argument, nullptr, 's'},
                                {"out", required_argument, nullptr, 'o'},
                                {"tag", required_argument, nullptr, 't'},
                                {"frames", required_argument, nullptr, 'n'},
                                {"period-ms", required_argument, nullptr, 'p'},
                                {"start-seq", required_argument, nullptr, 'q'},
                                {"pause-at", required_argument, nullptr, 'a'},
                                {"go-file", required_argument, nullptr, 'g'},
                                {"linger-s", required_argument, nullptr, 'l'},
                                {"help", no_argument, nullptr, 'h'},
                                {nullptr, no_argument, nullptr, 0}};
    while (true) {
        const int opt = getopt_long(argc, argv, "s:o:t:n:p:q:a:g:l:h", long_opts, nullptr);
        if (opt == -1) {
            break;
        }
        switch (opt) {
            case 's':
                manifest = optarg;
                break;
            case 'o':
                out_dir = optarg;
                break;
            case 't':
                tag = optarg;
                break;
            case 'n':
                frames = std::strtoull(optarg, nullptr, 10);
                break;
            case 'p':
                period_ms = std::strtoull(optarg, nullptr, 10);
                break;
            case 'q':
                start_seq = std::strtoull(optarg, nullptr, 10);
                break;
            case 'a':
                pause_at = ParseList(optarg);
                break;
            case 'g':
                go_file = optarg;
                break;
            case 'l':
                linger_s = std::strtoull(optarg, nullptr, 10);
                break;
            case 'h':
                PrintHelp();
                return 0;
            default:
                PrintHelp();
                return 1;
        }
    }
    if (manifest.empty() || out_dir.empty()) {
        PrintHelp();
        return 1;
    }

    Logs logs;
    logs.events = std::fopen((out_dir + "/" + tag + "_events.log").c_str(), "a");
    logs.frames = std::fopen((out_dir + "/" + tag + "_frames.bin").c_str(), "ab");
    if (logs.events == nullptr || logs.frames == nullptr) {
        std::cerr << "cannot open the log files in " << out_dir << std::endl;
        return 1;
    }
    logs.Event("START pid=" + std::to_string(::getpid()) + " start_seq=" + std::to_string(start_seq) +
               " frames=" + std::to_string(frames) + " period_ms=" + std::to_string(period_ms));

    score::mw::com::runtime::InitializeRuntime(
        score::mw::com::runtime::RuntimeConfiguration{score::filesystem::Path{manifest}});

    auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{"de4sdv/aebs_signal_frame"});
    if (!specifier.has_value()) {
        logs.Event("ERROR instance_specifier");
        return 2;
    }
    auto skeleton_result = de4sdv_spike::AebsSignalFrameSkeleton::Create(specifier.value());
    if (!skeleton_result.has_value()) {
        logs.Event("ERROR skeleton_create " + std::string{skeleton_result.error().Message()});
        return 3;
    }
    auto skeleton = std::move(skeleton_result).value();
    const auto offer_result = skeleton.OfferService();
    if (!offer_result.has_value()) {
        logs.Event("ERROR offer_service " + std::string{offer_result.error().Message()});
        return 4;
    }
    logs.Event("OFFERED");
    Touch(out_dir + "/" + tag + ".offered");

    if (!go_file.empty()) {
        if (!WaitForFile(go_file)) {
            skeleton.StopOfferService();
            logs.Event("STOP_OFFER before_go");
            return 0;
        }
        logs.Event("GO");
    }

    std::vector<std::uint8_t> frame;
    std::uint64_t seq = start_seq;
    std::uint64_t attempted = 0;
    std::uint64_t sent_ok = 0;
    const auto period = std::chrono::milliseconds(period_ms);
    auto next = std::chrono::steady_clock::now();
    while (!g_stop.load() && (frames == 0 || attempted < frames)) {
        const std::uint64_t t_ns = NowNs();
        BuildFrame(seq, t_ns, frame);
        auto sample_result = skeleton.aebs_signal_frame_.Allocate();
        if (!sample_result.has_value()) {
            logs.Event("ALLOC_FAIL seq=" + std::to_string(seq) + " " +
                       std::string{sample_result.error().Message()});
        } else {
            auto sample = std::move(sample_result).value();
            sample->size = frame.size();
            std::memcpy(sample->data, frame.data(), frame.size());
            const auto send_result = skeleton.aebs_signal_frame_.Send(std::move(sample));
            if (!send_result.has_value()) {
                logs.Event("SEND_FAIL seq=" + std::to_string(seq) + " " +
                           std::string{send_result.error().Message()});
            } else {
                logs.Frame(seq, t_ns, frame);
                logs.Event("SENT seq=" + std::to_string(seq) + " len=" + std::to_string(frame.size()));
                ++sent_ok;
            }
        }
        ++attempted;
        if (pause_at.count(seq) != 0U) {
            logs.Event("PAUSED seq=" + std::to_string(seq));
            Touch(out_dir + "/" + tag + ".paused-" + std::to_string(seq));
            if (!WaitForFile(out_dir + "/resume-" + std::to_string(seq))) {
                break;
            }
            logs.Event("RESUMED seq=" + std::to_string(seq));
            next = std::chrono::steady_clock::now();
        }
        ++seq;
        next += period;
        SleepUntil(next);
    }
    logs.Event("DONE attempted=" + std::to_string(attempted) + " sent=" + std::to_string(sent_ok) +
               " last_seq=" + std::to_string(seq - 1U));
    Touch(out_dir + "/" + tag + ".done");

    const auto linger_end = std::chrono::steady_clock::now() + std::chrono::seconds(linger_s);
    SleepUntil(linger_end);

    skeleton.StopOfferService();
    logs.Event("STOP_OFFER");
    std::fclose(logs.frames);
    logs.Event("EXIT");
    std::fclose(logs.events);
    return 0;
}
