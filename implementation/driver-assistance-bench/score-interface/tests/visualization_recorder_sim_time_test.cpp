// A functional test of the visualization recorder's sim_time_s column (patch 0001, brief item B3), against the
// patched tree's recorder and upstream's visualization sources at the pin. Built and run by
// test_score_interface.py when a VisionPilot clone, the ONNX Runtime and Eigen headers and OpenCV 4 are at hand.
// The encoder is the recorder's ffmpeg route with a stand-in ffmpeg that reads the frames and discards them.
//
// Each pass sets the capture simulation time of frame i to 100 + 0.05 i before its hand-off, except every third
// pass, which sets none (as in a run without the S-CORE interface): its row must leave sim_time_s empty, and it must
// not inherit the time of the pass before. Usage: visualization_recorder_sim_time_test <passes>
//   (DE4SDV_VISUALIZATION_RECORD and DE4SDV_VISUALIZATION_ENCODER=ffmpeg set by the caller)
#include <de4sdv/visualization_recorder.hpp>
#include <de4sdv/loop_stamps.hpp>

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <thread>

int main(int argc, char** argv)
{
    const int passes = argc > 1 ? std::atoi(argv[1]) : 30;
    const cv::Size net(1024, 512);
    auto recorder = de4sdv::VisualizationRecorder::from_env(net);
    if (!recorder)
    {
        std::fprintf(stderr, "DE4SDV_VISUALIZATION_RECORD is not set\n");
        return 2;
    }
    cv::Mat resized(net, CV_8UC3, cv::Scalar(40, 80, 120));
    cv::Mat H = (cv::Mat_<double>(3, 3) << 0.002, -0.001, -9.2, 0.0066, -0.0004, -3.3, 0.0001, -0.004, 1.0);
    Plan plan{};
    plan.acceleration = -1.0;
    plan.steering = {0.0, 0.01, 0.02};
    for (int i = 1; i <= passes; ++i)
    {
        visionpilot::models::InferenceFrameResult r;
        r.frame_id = static_cast<uint64_t>(i);
        if (i % 3 != 0) recorder->set_pass_sim_time(100.0 + 0.05 * i);
        recorder->submit(resized, r, plan, 5.0, H, 13.9, de4sdv::now_ns());
        std::this_thread::sleep_for(std::chrono::milliseconds(40));
    }
    recorder->stop();
    const auto s = recorder->stats();
    std::printf("RESULT submitted=%llu written=%llu dropped=%llu failed=%llu\n",
                static_cast<unsigned long long>(s.submitted), static_cast<unsigned long long>(s.written),
                static_cast<unsigned long long>(s.dropped), static_cast<unsigned long long>(s.failed));
    return s.written > 0 ? 0 : 1;
}
