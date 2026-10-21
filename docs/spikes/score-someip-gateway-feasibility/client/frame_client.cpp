// DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
//
// Guest-side receiver: a COVESA vsomeip 3.7.6 client that hosts its own
// routing (it is the only vsomeip application of the guest network domain),
// requests the AEBS signal frame service, subscribes to its eventgroup over a
// reliable (TCP) event, and records every received payload with its
// CLOCK_MONOTONIC receive time. It stands in for the someipReceiver of the
// phase-8 model; it does not re-serve the stream to an ingress.
//
// Outputs in --out:
//   client_events.log    text, "<mono_ns> <EVENT> k=v ..."
//   client_payloads.bin  records (u64 recv_ns, u32 len, len bytes), host order
// Control files in --control-dir (renamed to *.done once handled):
//   unsubscribe, resubscribe, probe

#include <getopt.h>
#include <sys/stat.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <mutex>
#include <set>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <vsomeip/vsomeip.hpp>

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

std::string Hex(unsigned value) {
    std::ostringstream stream;
    stream << "0x" << std::hex << value;
    return stream.str();
}

class Logs {
   public:
    bool Open(const std::string& out_dir) {
        events_ = std::fopen((out_dir + "/client_events.log").c_str(), "a");
        payloads_ = std::fopen((out_dir + "/client_payloads.bin").c_str(), "ab");
        return events_ != nullptr && payloads_ != nullptr;
    }

    void Event(const std::string& line) {
        std::lock_guard<std::mutex> lock(mutex_);
        const std::uint64_t now = NowNs();
        std::fprintf(events_, "%llu %s\n", static_cast<unsigned long long>(now), line.c_str());
        std::fflush(events_);
        std::cout << now << " [frame_client] " << line << std::endl;
    }

    void Payload(std::uint64_t recv_ns, const vsomeip::byte_t* data, std::uint32_t len) {
        std::lock_guard<std::mutex> lock(mutex_);
        std::fwrite(&recv_ns, sizeof(recv_ns), 1, payloads_);
        std::fwrite(&len, sizeof(len), 1, payloads_);
        if (len > 0U) {
            std::fwrite(data, 1, len, payloads_);
        }
        std::fflush(payloads_);
    }

    void Close() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (payloads_ != nullptr) {
            std::fclose(payloads_);
            payloads_ = nullptr;
        }
        if (events_ != nullptr) {
            std::fclose(events_);
            events_ = nullptr;
        }
    }

   private:
    std::mutex mutex_;
    FILE* events_{nullptr};
    FILE* payloads_{nullptr};
};

struct Options {
    std::string out_dir;
    std::string control_dir;
    std::string app_name{"frame_client"};
    vsomeip::service_t service{0x4dee};
    vsomeip::instance_t instance{0x0001};
    vsomeip::event_t event{0x8001};
    vsomeip::eventgroup_t eventgroup{0x0001};
    vsomeip::major_version_t major{0x01};
    vsomeip::method_t probe_method{0x0001};
};

unsigned long ParseNumber(const char* text) { return std::strtoul(text, nullptr, 0); }

void PrintHelp() {
    std::cout << "frame_client --out <dir> [--control-dir <dir>] [--app <name>]\n"
                 "  [--service 0x4dee] [--instance 0x1] [--event 0x8001] [--eventgroup 0x1]\n"
                 "  [--major 1] [--probe-method 0x1]\n";
}

bool TakeControl(const std::string& dir, const std::string& name) {
    if (dir.empty()) {
        return false;
    }
    const std::string path = dir + "/" + name;
    if (!FileExists(path)) {
        return false;
    }
    std::rename(path.c_str(), (path + ".done").c_str());
    return true;
}

}  // namespace

int main(int argc, char* argv[]) {
    std::signal(SIGTERM, OnSignal);
    std::signal(SIGINT, OnSignal);

    Options opts;
    const option long_opts[] = {{"out", required_argument, nullptr, 'o'},
                                {"control-dir", required_argument, nullptr, 'c'},
                                {"app", required_argument, nullptr, 'a'},
                                {"service", required_argument, nullptr, 's'},
                                {"instance", required_argument, nullptr, 'i'},
                                {"event", required_argument, nullptr, 'e'},
                                {"eventgroup", required_argument, nullptr, 'g'},
                                {"major", required_argument, nullptr, 'm'},
                                {"probe-method", required_argument, nullptr, 'p'},
                                {"help", no_argument, nullptr, 'h'},
                                {nullptr, no_argument, nullptr, 0}};
    while (true) {
        const int opt = getopt_long(argc, argv, "o:c:a:s:i:e:g:m:p:h", long_opts, nullptr);
        if (opt == -1) {
            break;
        }
        switch (opt) {
            case 'o':
                opts.out_dir = optarg;
                break;
            case 'c':
                opts.control_dir = optarg;
                break;
            case 'a':
                opts.app_name = optarg;
                break;
            case 's':
                opts.service = static_cast<vsomeip::service_t>(ParseNumber(optarg));
                break;
            case 'i':
                opts.instance = static_cast<vsomeip::instance_t>(ParseNumber(optarg));
                break;
            case 'e':
                opts.event = static_cast<vsomeip::event_t>(ParseNumber(optarg));
                break;
            case 'g':
                opts.eventgroup = static_cast<vsomeip::eventgroup_t>(ParseNumber(optarg));
                break;
            case 'm':
                opts.major = static_cast<vsomeip::major_version_t>(ParseNumber(optarg));
                break;
            case 'p':
                opts.probe_method = static_cast<vsomeip::method_t>(ParseNumber(optarg));
                break;
            case 'h':
                PrintHelp();
                return 0;
            default:
                PrintHelp();
                return 1;
        }
    }
    if (opts.out_dir.empty()) {
        PrintHelp();
        return 1;
    }

    Logs logs;
    if (!logs.Open(opts.out_dir)) {
        std::cerr << "cannot open the log files in " << opts.out_dir << std::endl;
        return 1;
    }
    logs.Event("START pid=" + std::to_string(::getpid()) + " vsomeip_app=" + opts.app_name);

    auto runtime = vsomeip::runtime::get();
    std::shared_ptr<vsomeip::application> app = runtime->create_application(opts.app_name);
    if (!app->init()) {
        logs.Event("INIT_FAIL");
        logs.Close();
        return 2;
    }
    logs.Event("INIT_OK");

    std::atomic<bool> unsubscribed_by_control{false};
    std::atomic<std::uint64_t> received{0};
    const std::set<vsomeip::eventgroup_t> groups{opts.eventgroup};

    auto subscribe = [&](const char* reason) {
        app->request_event(opts.service, opts.instance, opts.event, groups,
                           vsomeip::event_type_e::ET_EVENT, vsomeip::reliability_type_e::RT_RELIABLE);
        app->subscribe(opts.service, opts.instance, opts.eventgroup, opts.major);
        logs.Event(std::string{"SUBSCRIBE_CALLED reason="} + reason);
    };

    app->register_state_handler([&](vsomeip::state_type_e state) {
        if (state == vsomeip::state_type_e::ST_REGISTERED) {
            logs.Event("STATE registered");
            app->request_service(opts.service, opts.instance, opts.major, vsomeip::ANY_MINOR);
            logs.Event("REQUEST_SERVICE service=" + Hex(opts.service) + " instance=" + Hex(opts.instance));
        } else {
            logs.Event("STATE deregistered");
        }
    });

    app->register_availability_handler(
        opts.service, opts.instance,
        [&](vsomeip::service_t service, vsomeip::instance_t instance, bool is_available) {
            logs.Event(std::string{"AVAILABLE value="} + (is_available ? "1" : "0") +
                       " service=" + Hex(service) + " instance=" + Hex(instance));
            if (is_available && !unsubscribed_by_control.load()) {
                subscribe("available");
            }
        });

    app->register_subscription_status_handler(
        opts.service, opts.instance, opts.eventgroup, opts.event,
        [&](const vsomeip::service_t, const vsomeip::instance_t, const vsomeip::eventgroup_t,
            const vsomeip::event_t, const std::uint16_t status) {
            logs.Event("SUBSCRIPTION_STATUS status=" + Hex(status));
        },
        true);

    // One handler for every method of the service, dispatched here, so that a
    // notification is never counted twice by two matching handlers.
    app->register_message_handler(
        opts.service, opts.instance, vsomeip::ANY_METHOD,
        [&](const std::shared_ptr<vsomeip::message>& message) {
            const std::uint64_t recv_ns = NowNs();
            const auto type = message->get_message_type();
            const auto payload = message->get_payload();
            const vsomeip::byte_t* data = payload ? payload->get_data() : nullptr;
            const std::uint32_t len = payload ? payload->get_length() : 0U;
            if (type == vsomeip::message_type_e::MT_NOTIFICATION && message->get_method() == opts.event) {
                logs.Payload(recv_ns, data, len);
                std::uint64_t seq = 0;
                if (data != nullptr && len >= 12U) {
                    for (int i = 4; i < 12; ++i) {
                        seq = (seq << 8U) | data[i];
                    }
                }
                const std::uint64_t count = ++received;
                logs.Event("MSG n=" + std::to_string(count) + " len=" + std::to_string(len) +
                           " seq=" + std::to_string(seq) + " session=" + Hex(message->get_session()) +
                           " reliable=" + (message->is_reliable() ? "1" : "0"));
            } else {
                logs.Event("OTHER_MESSAGE method=" + Hex(message->get_method()) +
                           " type=" + Hex(static_cast<unsigned>(type)) +
                           " return_code=" + Hex(static_cast<unsigned>(message->get_return_code())) +
                           " len=" + std::to_string(len));
            }
        });

    std::thread control([&]() {
        while (!g_stop.load()) {
            if (TakeControl(opts.control_dir, "unsubscribe")) {
                unsubscribed_by_control.store(true);
                app->unsubscribe(opts.service, opts.instance, opts.eventgroup);
                logs.Event("UNSUBSCRIBE_CALLED");
            }
            if (TakeControl(opts.control_dir, "resubscribe")) {
                unsubscribed_by_control.store(false);
                subscribe("control");
            }
            if (TakeControl(opts.control_dir, "probe")) {
                // REQ-MW-016 probe: application data from the guest towards the
                // host, as a request with a return and a fire-and-forget request.
                const std::vector<vsomeip::byte_t> bytes{'P', 'R', 'O', 'B', 'E'};
                auto request = runtime->create_request(true);
                request->set_service(opts.service);
                request->set_instance(opts.instance);
                request->set_method(opts.probe_method);
                request->set_interface_version(opts.major);
                request->set_payload(runtime->create_payload(bytes));
                app->send(request);
                auto fire_and_forget = runtime->create_request(true);
                fire_and_forget->set_service(opts.service);
                fire_and_forget->set_instance(opts.instance);
                fire_and_forget->set_method(opts.probe_method);
                fire_and_forget->set_interface_version(opts.major);
                fire_and_forget->set_message_type(vsomeip::message_type_e::MT_REQUEST_NO_RETURN);
                fire_and_forget->set_payload(runtime->create_payload(bytes));
                app->send(fire_and_forget);
                logs.Event("PROBE_SENT method=" + Hex(opts.probe_method));
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        logs.Event("STOPPING received=" + std::to_string(received.load()));
        app->release_service(opts.service, opts.instance);
        app->stop();
    });

    app->start();
    g_stop.store(true);
    if (control.joinable()) {
        control.join();
    }
    logs.Event("EXIT received=" + std::to_string(received.load()));
    logs.Close();
    return 0;
}
