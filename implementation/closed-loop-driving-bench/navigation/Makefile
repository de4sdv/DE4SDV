# DE4SDV closed-loop driving bench, S3 navigation inputs.
#
#   make native   build upstream's native rasterizer, as-is, from .upstream/
#   make lib      build libde4sdv_navigation_raster (links the native one)
#   make cli      build the parity/unit driver used by the Python tests
#   make test     run the Python test suite (needs .venv with numpy+pytest)
#
# Everything lands in build/; no upstream file is modified.

CXX ?= c++
PYTHON ?= .venv/bin/python
UPSTREAM ?= .upstream
NATIVE_DIR := $(UPSTREAM)/Model/navigation/native
INTERFACES := ../interfaces/include

CXXFLAGS := -std=c++17 -O2 -g -fPIC -Wall -Wextra -I. -I$(NATIVE_DIR) -I$(INTERFACES)
BUILD := build

.PHONY: all native lib cli bench profile test clean

all: native lib cli bench parity

$(BUILD):
	mkdir -p $(BUILD)

native: | $(BUILD)
	$(PYTHON) $(NATIVE_DIR)/build.py --output $(BUILD)/libnavigation_rasterizer.so

lib: $(BUILD)/libde4sdv_navigation_raster.so

$(BUILD)/libde4sdv_navigation_raster.so: navigation_raster.cpp navigation_raster.h native | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared navigation_raster.cpp -o $@ \
		-L$(BUILD) -lnavigation_rasterizer -Wl,-rpath,'$$ORIGIN'

cli: $(BUILD)/raster_cli

$(BUILD)/raster_cli: tests/raster_cli.cpp navigation_raster.h lib | $(BUILD)
	$(CXX) $(CXXFLAGS) tests/raster_cli.cpp -o $@ \
		-L$(BUILD) -lde4sdv_navigation_raster \
		-Wl,-rpath,'$$ORIGIN'

# Wall-clock probe for one render on a real exported map (map route [n]).
bench: $(BUILD)/render_cost

$(BUILD)/render_cost: tests/render_cost.cpp navigation_raster.h lib | $(BUILD)
	$(CXX) $(CXXFLAGS) tests/render_cost.cpp -o $@ \
		-L$(BUILD) -lde4sdv_navigation_raster \
		-Wl,-rpath,'$$ORIGIN'

# Same probe, split into zero-fill / packing / native call.
profile: $(BUILD)/render_profile

$(BUILD)/render_profile: tests/render_profile.cpp navigation_raster.h lib | $(BUILD)
	$(CXX) $(CXXFLAGS) -I$(NATIVE_DIR) tests/render_profile.cpp -o $@ \
		-L$(BUILD) -lde4sdv_navigation_raster -lnavigation_rasterizer \
		-Wl,-rpath,'$$ORIGIN'

# Differential fast-vs-reference sweep on a real map (map route).
parity: $(BUILD)/parity_sweep

$(BUILD)/parity_sweep: tests/parity_sweep.cpp navigation_raster.h lib | $(BUILD)
	$(CXX) $(CXXFLAGS) tests/parity_sweep.cpp -o $@ \
		-L$(BUILD) -lde4sdv_navigation_raster \
		-Wl,-rpath,'$$ORIGIN'

test: all
	$(PYTHON) -m pytest -q tests

clean:
	rm -rf $(BUILD)
