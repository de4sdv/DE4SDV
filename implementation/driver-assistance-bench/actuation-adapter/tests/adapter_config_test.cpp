// Tests of the actuation adapter's run configuration (adapter_config.h).
#include <string>

#include "adapter_config.h"
#include "check.h"

using de4sdv::driver_assistance::actuation::AdapterConfig;
using de4sdv::driver_assistance::actuation::LoadAdapterConfigFile;
using de4sdv::driver_assistance::actuation::ParseAdapterConfig;
using de4sdv::driver_assistance::actuation::test::Finish;

namespace {

bool Parses(const std::string& json, AdapterConfig* out = nullptr) {
  bool ok = false;
  std::string error;
  const AdapterConfig config = ParseAdapterConfig(json, &ok, &error);
  if (out != nullptr) *out = config;
  return ok;
}

void TestDefaultsFromAnEmptyObject() {
  AdapterConfig config;
  CHECK(Parses("{}", &config));
  CHECK(config.carla_host == "127.0.0.1");
  CHECK(config.carla_port == 2000);
  CHECK_EQ_D(config.client_timeout_s, 30.0);
  CHECK(config.hero_role_name == "hero");
  CHECK_EQ_D(config.hero_wait_s, 20.0);
}

void TestEveryKeyIsRead() {
  AdapterConfig config;
  CHECK(Parses("{\"carla_host\":\"10.164.0.2\",\"carla_port\":2010,\"client_timeout_s\":12.5,"
               "\"hero_role_name\":\"ego\",\"hero_wait_s\":3}",
               &config));
  CHECK(config.carla_host == "10.164.0.2");
  CHECK(config.carla_port == 2010);
  CHECK_EQ_D(config.client_timeout_s, 12.5);
  CHECK(config.hero_role_name == "ego");
  CHECK_EQ_D(config.hero_wait_s, 3.0);
}

void TestRefusals() {
  CHECK(!Parses(""));
  CHECK(!Parses("[]"));
  CHECK(!Parses("{\"carla_port\":0}"));
  CHECK(!Parses("{\"carla_port\":65536}"));
  CHECK(!Parses("{\"carla_port\":2000.5}"));
  CHECK(!Parses("{\"carla_port\":\"2000\"}"));
  CHECK(!Parses("{\"client_timeout_s\":0}"));
  CHECK(!Parses("{\"client_timeout_s\":-1}"));
  CHECK(!Parses("{\"hero_wait_s\":0}"));
  CHECK(!Parses("{\"carla_host\":\"\"}"));
  CHECK(!Parses("{\"carla_host\":7}"));
  CHECK(!Parses("{\"hero_role_name\":\"\"}"));
  CHECK(!Parses("{\"unknown\":1}"));
  // The rules of MAP-DRIVING-DA-COMMAND are the model's, not a run's.
  CHECK(!Parses("{\"jerk\":5.0}"));
  CHECK(!Parses("{\"max_delay_s\":0.2}"));
  CHECK(Parses("{\"carla_port\":1}"));
  CHECK(Parses("{\"carla_port\":65535}"));
}

void TestTheShippedFileParses(const char* path) {
  bool ok = false;
  std::string error;
  const AdapterConfig config = LoadAdapterConfigFile(path, &ok, &error);
  CHECK(ok);
  CHECK(config.hero_role_name == "hero");
  bool missing_ok = true;
  LoadAdapterConfigFile(std::string(path) + ".absent", &missing_ok, &error);
  CHECK(!missing_ok);
}

}  // namespace

int main(int argc, char** argv) {
  TestDefaultsFromAnEmptyObject();
  TestEveryKeyIsRead();
  TestRefusals();
  if (argc > 1) TestTheShippedFileParses(argv[1]);
  return Finish("adapter_config_test");
}
