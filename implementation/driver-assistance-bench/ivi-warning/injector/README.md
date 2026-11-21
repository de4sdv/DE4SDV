# Test publisher of the warning request (p10-3)

Status: draft, not yet validated. Beyond the host's tests in `tests/`, the publisher ran on the S-CORE host in p10-3 run
2 (SID 20261119T130414Z, 2026-11-19, `410293bb`): the IVI guest received 21 of its 21 test requests (conditional on a
permissive IVI). In p10-1 try 4 (SID 20261119T160111Z, 2026-11-19, `eae0a6ef`) it gave C5's three sends; C5 is not run
by design.

## The problem

p10-3 measures the warning path from the S-CORE host to the IVI display: gatewayd, someipd, the VXLAN segment and
the guests. It needs warning requests with known issue times and known edges. The candidate cannot give them on
demand. A test publisher sends them in the candidate's place. What it shows is evidence of the path, not of the
candidate (brief R1).

## What it does

`warning_injector --sequence <file> --log <jsonl>` is an S-CORE application. It offers the candidate's mw::com
instance `de4sdv/driver_assistance/warning_request` (service 7412, ICD.md). It then sends each line of the sequence
at its offset after a lead-in:

- The payload is the 8 SOME/IP bytes of `payloads.h` (`EncodeWarningRequestSomeip`). They go in a
  `PreSerializedData<2048>` sample of size 8, as score-interface's `lola_bindings.cpp` sends them.
- The sequence (`config/p10_3_sequence.txt`) has one line per request: `<offset_s> <true|false> <issue_time_s>`.
  `injection_plan.h` refuses a sequence whose offsets go backward, whose issue times repeat (each guest receipt must
  match one send by its bytes), or whose first request is a true.
- Each send is one `out.warning_request` line in the log. The line carries the S-CORE host's real time and monotonic
  time, read just before and just after the send. With the clock records of the inject script, they bound the
  0.1 s share of the path (brief R9).

The manifest `mw_com_config_warning_injector.json` has the candidate's instance as it is (QM, 20 slots, one
subscriber) and the candidate's global ASIL B. Application id 3415 is this lane's proposal. gatewayd (QM) so
receives from an ASIL B process, as it will from the candidate. p10-1's check C5 relies on that.

The test publisher and the candidate offer the same instance, so they never run together.
`../scripts/inject_warning_requests.sh` (`ENTRY_SCORE_INJECT`) refuses to run unless the S-CORE side is up in mode
path (`../../score-path/scripts/`).

Exit statuses: 0 every send went out; 1 usage; 2 `MW_COM_CONFIG` unset or the log not writable; 3 a bad sequence;
4 the offer failed; 5 a send failed; 6 stopped by a signal.

## Tests

```bash
python -m pytest -q implementation/driver-assistance-bench/ivi-warning/injector/tests
```

- `injector_test.cpp` builds with g++ as C++17 and C++20, and tests the plan and the shell with a fake sink and
  fake clocks. The payload bytes are compared with Python's `struct` at test time.
- `injector_driver.cpp` runs the real plan and shell with a sink that writes each payload as hex. The script tests
  run it as the staged `warning_injector` against the fake Launch Manager of `../../score-path/tests/`.
- The main is compiled for syntax against the closed-loop bench's mw::com mock (not S-CORE).

## What only the S-CORE host shows

- that the Bazel build links the main against Communication v0.6.0;
- that mw::com accepts the offer with the candidate's manifest values, and that gatewayd forwards each sample to
  someipd and over SOME/IP;
- the receipt on the guests and the display's and the sound's times (p10-3 itself).
