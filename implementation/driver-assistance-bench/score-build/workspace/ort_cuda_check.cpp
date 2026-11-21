// DE4SDV driver-assistance bench (INC-DRIVING-002): does ONNX Runtime's CUDA provider load and run in this process?
//
// Usage: ort_cuda_check [--cpu-only] [<model.onnx> [runs]]
//   1. prints the ONNX Runtime version and its available providers; CUDAExecutionProvider must be among them;
//   2. without --cpu-only: appends the CUDA provider (device 0) to the session options. That loads
//      libonnxruntime_providers_cuda.so and with it the CUDA and cuDNN runtime (libcudart.so.12, libcublas.so.12,
//      libcublasLt.so.12, libcufft.so.11, libcurand.so.10, libcudnn.so.9); a missing library fails here;
//   3. with a model: creates the session, feeds zeros of each input's shape (dynamic dimensions taken as 1) and runs
//      it `runs` times (default 10), printing each run's wall time.
// Exit status 0 when every step that ran passed, 1 otherwise. The last line is "ORT_CUDA_CHECK PASS" or
// "ORT_CUDA_CHECK FAIL <reason>".
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <string>
#include <vector>

#include <onnxruntime_cxx_api.h>

namespace {

int Fail(const std::string& reason) {
  std::printf("ORT_CUDA_CHECK FAIL %s\n", reason.c_str());
  return 1;
}

std::size_t ElementCount(const std::vector<std::int64_t>& shape) {
  std::size_t count = 1;
  for (const std::int64_t dim : shape) {
    count *= static_cast<std::size_t>(dim);
  }
  return count;
}

}  // namespace

int main(int argc, char** argv) {
  bool cpu_only = false;
  std::vector<std::string> positional;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--cpu-only") == 0) {
      cpu_only = true;
    } else {
      positional.emplace_back(argv[i]);
    }
  }
  const std::string model = positional.empty() ? std::string{} : positional[0];
  const int runs = positional.size() > 1 ? std::atoi(positional[1].c_str()) : 10;

  try {
    std::printf("onnxruntime version %s\n", Ort::GetVersionString().c_str());
    bool cuda_listed = false;
    for (const std::string& provider : Ort::GetAvailableProviders()) {
      std::printf("available provider %s\n", provider.c_str());
      cuda_listed = cuda_listed || provider == "CUDAExecutionProvider";
    }
    if (!cuda_listed) {
      return Fail("CUDAExecutionProvider is not in this ONNX Runtime build");
    }

    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "ort_cuda_check"};
    Ort::SessionOptions options;
    if (!cpu_only) {
      OrtCUDAProviderOptions cuda_options{};
      cuda_options.device_id = 0;
      options.AppendExecutionProvider_CUDA(cuda_options);
      std::printf("CUDA provider appended (device 0): libonnxruntime_providers_cuda.so and the CUDA runtime loaded\n");
    }
    if (model.empty()) {
      std::printf("ORT_CUDA_CHECK PASS\n");
      return 0;
    }

    Ort::Session session{env, model.c_str(), options};
    Ort::AllocatorWithDefaultOptions allocator;
    Ort::MemoryInfo memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);

    std::vector<std::string> input_names;
    std::vector<std::vector<std::int64_t>> input_shapes;
    std::vector<std::vector<float>> input_data;
    std::vector<Ort::Value> inputs;
    for (std::size_t i = 0; i < session.GetInputCount(); ++i) {
      input_names.emplace_back(session.GetInputNameAllocated(i, allocator).get());
      std::vector<std::int64_t> shape = session.GetInputTypeInfo(i).GetTensorTypeAndShapeInfo().GetShape();
      for (std::int64_t& dim : shape) {
        if (dim < 1) {
          dim = 1;
        }
      }
      input_shapes.push_back(shape);
    }
    for (std::size_t i = 0; i < input_shapes.size(); ++i) {
      input_data.emplace_back(ElementCount(input_shapes[i]), 0.0F);
    }
    for (std::size_t i = 0; i < input_shapes.size(); ++i) {
      inputs.push_back(Ort::Value::CreateTensor<float>(memory, input_data[i].data(), input_data[i].size(),
                                                       input_shapes[i].data(), input_shapes[i].size()));
    }
    std::vector<std::string> output_names;
    for (std::size_t i = 0; i < session.GetOutputCount(); ++i) {
      output_names.emplace_back(session.GetOutputNameAllocated(i, allocator).get());
    }
    std::vector<const char*> input_ptrs;
    std::vector<const char*> output_ptrs;
    for (const std::string& name : input_names) {
      input_ptrs.push_back(name.c_str());
    }
    for (const std::string& name : output_names) {
      output_ptrs.push_back(name.c_str());
    }
    std::printf("model %s: %zu inputs, %zu outputs\n", model.c_str(), input_names.size(), output_names.size());

    for (int run = 1; run <= runs; ++run) {
      const auto start = std::chrono::steady_clock::now();
      std::vector<Ort::Value> outputs = session.Run(Ort::RunOptions{nullptr}, input_ptrs.data(), inputs.data(),
                                                    inputs.size(), output_ptrs.data(), output_ptrs.size());
      const auto end = std::chrono::steady_clock::now();
      const double ms = std::chrono::duration<double, std::milli>(end - start).count();
      std::printf("run %d: %zu outputs, %.3f ms\n", run, outputs.size(), ms);
      if (outputs.size() != output_names.size()) {
        return Fail("a run returned fewer outputs than the model declares");
      }
    }
    std::printf("ORT_CUDA_CHECK PASS\n");
    return 0;
  } catch (const std::exception& error) {
    return Fail(error.what());
  }
}
