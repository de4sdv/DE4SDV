#!/usr/bin/env bash
# drivingAgent's C++ units (agent/cc): the decision logic (agent_logic), the frame store
# (frame_store + pace_signal), the kinematics (ego_motion.h), the route listener, the nav
# prefetch (nav_prefetch.h) and the navigation input. Plain -O2 with warnings as errors, AddressSanitizer +
# UndefinedBehaviorSanitizer, ThreadSanitizer for the threaded units, the records-against-the-
# evaluators check, and with --mutations the mutation probes.
#   run_tests.sh [--mutations]
# Needs g++ (C++17) and a Python 3 with numpy for the evaluators (PYTHON, default:
# case-evaluators/.venv/bin/python when present, else python3). The navigation input needs
# upstream's renderer in navigation/.upstream and a bench map and route: NAV_MAP, NAV_ROUTE
# (map.json and route.json from navigation/carla_map_export.py and route_from_carla.py); without
# them its steps print SKIP, never ok.
set -uo pipefail
CC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="$(cd "$CC_DIR/../.." && pwd)"
INC="$BENCH/interfaces/include"
OUT="$CC_DIR/.build"
mkdir -p "$OUT"
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  if [ -x "$BENCH/case-evaluators/.venv/bin/python" ]; then PYTHON="$BENCH/case-evaluators/.venv/bin/python"; else PYTHON=python3; fi
fi
FAILED=0
step() {  # name, command...
  local name=$1; shift
  if "$@" > "$OUT/$name.log" 2>&1; then
    echo "ok    $name :: $(grep -v '^$' "$OUT/$name.log" | tail -1)"
  else
    echo "FAIL  $name (log: $OUT/$name.log)"; grep -E "FAIL|error|ERROR|runtime error" "$OUT/$name.log" | head -8
    FAILED=1
  fi
}
san_clean() {  # log: no sanitizer report
  ! grep -q -E "WARNING: ThreadSanitizer|ERROR: AddressSanitizer|LeakSanitizer|runtime error" "$1"
}
W=(-std=c++17 -Wall -Wextra -Werror)
LOGIC=("-I$CC_DIR" "-I$INC" "$CC_DIR/tests/agent_logic_test.cpp" "$CC_DIR/agent_logic.cpp" "$CC_DIR/json_lite.cpp")
FS=("-I$CC_DIR" "$CC_DIR/frame_store.cpp" "$CC_DIR/pace_signal.cpp")
cd "$CC_DIR"

step build_logic        g++ "${W[@]}" -O2 "${LOGIC[@]}" -o "$OUT/agent_logic_test"
step logic              "$OUT/agent_logic_test"
step build_logic_asan   g++ "${W[@]}" -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer "${LOGIC[@]}" -o "$OUT/agent_logic_test_asan"
step logic_asan         "$OUT/agent_logic_test_asan"
san_clean "$OUT/logic_asan.log" || { echo "FAIL  logic_asan: sanitizer report"; FAILED=1; }
step records            env AGENT_LOGIC_TEST_BIN="$OUT/agent_logic_test" "$PYTHON" "$CC_DIR/tests/test_records_against_evaluators.py"

step build_fs           g++ "${W[@]}" -O2 -pthread "$CC_DIR/tests/frame_store_test.cpp" "${FS[@]}" -o "$OUT/frame_store_test"
step frame_store        "$OUT/frame_store_test"
step build_fs_stress    g++ "${W[@]}" -O2 -pthread "$CC_DIR/tests/frame_store_stress_test.cpp" "${FS[@]}" -o "$OUT/frame_store_stress_test"
step frame_store_stress "$OUT/frame_store_stress_test"
for SAN in thread "address,undefined"; do
  TAG=${SAN%%,*}
  step build_fs_$TAG        g++ "${W[@]}" -O1 -g -fsanitize=$SAN -fno-omit-frame-pointer -pthread "$CC_DIR/tests/frame_store_test.cpp" "${FS[@]}" -o "$OUT/frame_store_test_$TAG"
  step frame_store_$TAG     env TSAN_OPTIONS=halt_on_error=0 "$OUT/frame_store_test_$TAG"
  san_clean "$OUT/frame_store_$TAG.log" || { echo "FAIL  frame_store_$TAG: sanitizer report"; FAILED=1; }
  step build_fs_stress_$TAG g++ "${W[@]}" -O1 -g -fsanitize=$SAN -fno-omit-frame-pointer -pthread "$CC_DIR/tests/frame_store_stress_test.cpp" "${FS[@]}" -o "$OUT/frame_store_stress_test_$TAG"
  step frame_store_stress_$TAG env TSAN_OPTIONS=halt_on_error=0 "$OUT/frame_store_stress_test_$TAG"
  san_clean "$OUT/frame_store_stress_$TAG.log" || { echo "FAIL  frame_store_stress_$TAG: sanitizer report"; FAILED=1; }
done

step build_prefetch      g++ "${W[@]}" -O2 -pthread "-I$CC_DIR" "$CC_DIR/tests/nav_prefetch_test.cpp" -o "$OUT/nav_prefetch_test"
step nav_prefetch        "$OUT/nav_prefetch_test"
for SAN in thread "address,undefined"; do
  TAG=${SAN%%,*}
  step build_prefetch_$TAG g++ "${W[@]}" -O1 -g -fsanitize=$SAN -fno-omit-frame-pointer -pthread "-I$CC_DIR" "$CC_DIR/tests/nav_prefetch_test.cpp" -o "$OUT/nav_prefetch_test_$TAG"
  step nav_prefetch_$TAG   env TSAN_OPTIONS=halt_on_error=0 "$OUT/nav_prefetch_test_$TAG"
  san_clean "$OUT/nav_prefetch_$TAG.log" || { echo "FAIL  nav_prefetch_$TAG: sanitizer report"; FAILED=1; }
done

step build_ego           g++ "${W[@]}" -O2 "-I$CC_DIR" "-I$INC" "$CC_DIR/tests/ego_motion_test.cpp" -o "$OUT/ego_motion_test"
step ego_motion          "$OUT/ego_motion_test"
step build_route         g++ "${W[@]}" -O2 -pthread "-I$CC_DIR" "-I$INC" "$CC_DIR/tests/route_listener_test.cpp" "$CC_DIR/route_listener.cpp" -o "$OUT/route_listener_test"
step route_listener      "$OUT/route_listener_test"
step build_route_thread  g++ "${W[@]}" -O1 -g -fsanitize=thread -pthread "-I$CC_DIR" "-I$INC" "$CC_DIR/tests/route_listener_test.cpp" "$CC_DIR/route_listener.cpp" -o "$OUT/route_listener_test_thread"
step route_listener_thread env TSAN_OPTIONS=halt_on_error=0 "$OUT/route_listener_test_thread"
san_clean "$OUT/route_listener_thread.log" || { echo "FAIL  route_listener_thread: sanitizer report"; FAILED=1; }

NAVD="$BENCH/navigation"
UPN="$NAVD/.upstream/Model/navigation/native"
NAV_OK=0
if [ -f "$UPN/navigation_rasterizer.cpp" ] && [ -f "${NAV_MAP:-/nonexistent}" ] && [ -f "${NAV_ROUTE:-/nonexistent}" ]; then
  NAV_OK=1
  NAV=("-I$CC_DIR" "-I$NAVD" "-I$UPN" "-I$INC" "$CC_DIR/tests/navigation_input_test.cpp" "$CC_DIR/route_listener.cpp" "$NAVD/navigation_raster.cpp" "$OUT/upstream_rasterizer.o")
  step build_upstream_raster g++ -std=c++17 -O3 -DNDEBUG -c "$UPN/navigation_rasterizer.cpp" -o "$OUT/upstream_rasterizer.o"
  step build_nav           g++ "${W[@]}" -O2 -pthread "${NAV[@]}" "$CC_DIR/navigation_input.cpp" -o "$OUT/navigation_input_test"
  step navigation_input    "$OUT/navigation_input_test" "$NAV_MAP" "$NAV_ROUTE"
  # One render at a time (the nav prefetch's thread and a render on the chain).
  step build_nav_thread    g++ "${W[@]}" -O1 -g -fsanitize=thread -pthread "${NAV[@]}" "$CC_DIR/navigation_input.cpp" -o "$OUT/navigation_input_test_thread"
  step navigation_input_thread env TSAN_OPTIONS=halt_on_error=0 "$OUT/navigation_input_test_thread" "$NAV_MAP" "$NAV_ROUTE"
  san_clean "$OUT/navigation_input_thread.log" || { echo "FAIL  navigation_input_thread: sanitizer report"; FAILED=1; }
else
  echo "SKIP  navigation_input (needs $UPN/navigation_rasterizer.cpp, NAV_MAP and NAV_ROUTE)"
fi

if [ "${1:-}" = "--mutations" ]; then
  step logic_mutations       "$PYTHON" "$CC_DIR/tests/agent_logic_mutations.py"
  step frame_store_mutations "$PYTHON" "$CC_DIR/tests/frame_store_mutations.py"
  step nav_prefetch_mutations "$PYTHON" "$CC_DIR/tests/nav_prefetch_mutations.py"
  if [ $NAV_OK -eq 1 ]; then
    # The coverage check must see a wrong pixel mapping: a mirrored lateral axis and swapped axes.
    i=0
    for mut in 's/ey = -s \* dx + c \* dy/ey = s * dx - c * dy/' \
               's/route_u8_\[corridor + row \* static_cast<std::size_t>(nav::kWidthPx) + col\]/route_u8_[corridor + (col % 450) * static_cast<std::size_t>(nav::kWidthPx) + (row % 300)]/'; do
      i=$((i + 1))
      sed "$mut" "$CC_DIR/navigation_input.cpp" > "$OUT/navigation_input_mut$i.cpp"
      if cmp -s "$CC_DIR/navigation_input.cpp" "$OUT/navigation_input_mut$i.cpp"; then
        echo "FAIL  navigation mutation $i did not apply"; FAILED=1; continue
      fi
      if g++ -std=c++17 -O2 -pthread "${NAV[@]}" "$OUT/navigation_input_mut$i.cpp" -o "$OUT/navigation_input_mut$i" > "$OUT/nav_mut$i.log" 2>&1 \
         && ! "$OUT/navigation_input_mut$i" "$NAV_MAP" "$NAV_ROUTE" >> "$OUT/nav_mut$i.log" 2>&1; then
        echo "ok    navigation mutation $i killed :: $(grep -E 'checks' "$OUT/nav_mut$i.log" | tail -1)"
      else
        echo "FAIL  navigation mutation $i survived (log: $OUT/nav_mut$i.log)"; FAILED=1
      fi
    done
  fi
  git -C "$CC_DIR" diff --quiet -- . 2>/dev/null || true
fi
[ $FAILED -eq 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $FAILED
