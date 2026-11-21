# Identity recorder (build item B4)

Status: draft, not yet validated. Beyond the host's tests in `tests/`, the recorder has run on the S-CORE host. In p10-1
try 4 (SID 20261119T160111Z, 2026-11-19, `eae0a6ef`) it reported running before `vision_pilot` and `actuation_adapter`
started (C1), and the late subscriber got its record 3632 ms after the first publication (C7). In S1 (SID
20261121T014447Z, 2026-11-21, `508649ba`) it wrote a candidate record in each of the 16 runs (the steering calibration,
the 14 runs and the stop run). VC-DRIVING-044, which reads the record, is inconclusive in S1: every run dropped camera
images.

## The problem

REQ-DRIVING-044 asks that every run names the candidate it judged, and that another engineer can re-derive that
identity. In INC-DRIVING-002 every build on the S-CORE path is VisionPilot at
`014e0e7a56ee8e597c2cab8175233f74edd9b856` plus changes upstream has not merged (the S-CORE interface and the
visualization recorder). So the record must carry the difference, the hash of every file the candidate's process
reads, and the launch settings. It must also exist before the candidate sends its first driving command. The
model gives this job to the `CandidateIdentityRecordingApplication`. It is an S-CORE application of its own, which
the Launch Manager starts first (MAP-DRIVING-DA-CANDIDATE-RECORD in
`driver_assistance_physical_software_realization.sysml`).

## What it does

`identity_recorder --run-dir <run>` runs under the Launch Manager as component `identity_recorder`, type `Reporting`
(`../launch-manager/config/launch_manager_config.json`). It runs these steps:

1. It finds and hashes its inputs (`record_inputs.h`) from the Launch Manager configuration, the way the
   processes find them:
   - the launch settings of every component, with the component's `deployment_config` over the defaults;
   - `vision_pilot.conf`, `H.yaml` and `homography_C_matrix.yaml` by upstream's own lookup at the pin. That is
     `config/<name>` in the candidate's working directory, else `/usr/share/visionpilot/config/<name>`
     (`VisionPilot/modules/common/src/utils.cpp:3-12`). The last two are the session's camera calibration
     (`DA_CAMERA_CALIBRATION_DIR`), which the start stages and names in `<out>/camera_calibration.json`
     (`../score-path/scripts/README.md`);
   - the three networks `autodrive`, `autosteer` and `autospeed` `_<model.precision>.onnx`
     (`modules/models/src/inference.cpp:72-73,102-104`);
   - the interface configuration (`DE4SDV_SCORE_INTERFACE_CONFIG`) and the candidate's mw::com manifest that its
     `mw_com.config` names;
   - every file that a component's process argument or environment variable names: the other mw::com manifests,
     the gateway configuration, the vsomeip configuration and `adapter.json`;
   - the serialized Launch Manager configuration (`etc/*.bin`), and every binary;
   - every file in the candidate's `LD_LIBRARY_PATH` (ONNX Runtime);
   - the ldconfig conf `/etc/ld.so.conf.d/de4sdv-cuda-*.conf` of `../score-build/install_gpu_runtime.sh`, and every
     shared library in each directory it lists (CUDA and cuDNN). These are the lead's answers of 2026-11-18;
   - the source difference: every `*.diff` in `<stage>/facts/`, checked against its `SHA256SUMS`. Today these are
     patches 0001, 0002 and 0003 of `../score-interface/`;
   - the upstream revision from `<stage>/facts/upstream_revision.txt`.
2. It writes `<run>/score/candidate_record.json` through a temporary file, `fsync` and `rename`
   (`candidate_record.h`, the record writer).
3. It offers `de4sdv/driver_assistance/candidate_record` (service 7413, `CandidateRecordEventPayload`) and sends the
   event once. The event holds the SHA-256 of the file, the revision, the size of the difference and the file's
   path.
4. It calls `score_mw_lifecycle_report_running()`. Only then does the Launch Manager start `vision_pilot` and
   `actuation_adapter`. If the report fails, it logs `lifecycle` `error` and keeps publishing. That is the lead's
   fallback (the component is then Native in effect). The log says so; the record does not.
5. It re-sends the event every 1 s until SIGTERM (ICD.md), so that a subscriber who comes late gets it.

A missing input ends the process before step 2, with no file, no event and no report. The Launch Manager's ready
timeout then expires and the candidate never starts. Exit statuses: 3 inputs, 4 write, 5 payload, 6 offer, 7 first
send. The log is `<run>/score/identityRecorder.jsonl` in the run log format of `../actuation-adapter/run_log.h`. Its
events are `start`, one `input` per hashed file, `record`, `offer`, `publish`, `lifecycle`, `error` and `stop`.

`candidate_record_probe` is the late subscriber of p10-1 (`../score-build/scripts/p10_1_check.sh`). It subscribes on
purpose after the record was published, then checks the event against the file (`record_probe.h`).

## The record

| Field | Model value (MAP-DRIVING-DA-CANDIDATE-RECORD, `RetainedAssistanceRunEvidence`) |
|---|---|
| `upstream_revision` | the upstream revision (`upstreamRevision`) |
| `source_difference` (`bytes`, `sha256`, `files[]` with each diff's text verbatim) | the difference of the built source against the revision (`sourceDifference`), never empty |
| `configuration_files[]` (`role`, `path`, `sha256`, `bytes`, `link_target`) | the SHA-256 of each configuration, calibration and manifest file (`configurationFileSha256`); the first five are the model's list in its order |
| `network_files[]` | the SHA-256 of each network file (`networkFileSha256`) |
| `launch_settings` (`launch_config_text` verbatim, `components[]` merged) | the launch settings verbatim, with the working directory (`launchSettings`) |
| `binaries[]`, `runtime_libraries[]`, `ldconfig_conf` | not in the model: the lead's answers of 2026-11-18 (binaries, and the CUDA/cuDNN/ORT libraries the ldconfig conf names) |
| `schema`, `mapping`, `host`, `record_path`, `written_real_ns`, `written_mono_ns`, `candidate` | bookkeeping: the record's time, for REQ-DRIVING-044's "record before the first command" |

Every SHA-256 is lowercase hex, and every value is a string or a count (the mapping's `dataTypeAndUnit`).

## What the model leaves open, and the choices here

- **The layout.** The model names the values, not a file format, field names or an order. The JSON above is this
  lane's proposal.
- **"The network files that the configuration selects."** This README reads them as the ONNX networks that
  `model.precision` selects. Upstream's `inference.cpp` names them so.
- **"The mw::com manifest."** The model names the candidate's manifest. The record hashes every manifest on the host,
  and puts the candidate's first.
- **The difference as text.** The model says the record carries the difference. The record embeds it verbatim, so
  the record alone is enough to re-derive the build (`scripts/check_candidate_record.py`). That makes the record
  about 110 KB.
- **Which libraries.** The model does not name libraries. The lead's answer adds the conf and the libraries it
  names. This lane also adds every file of the candidate's `LD_LIBRARY_PATH`.
- **The serialized Launch Manager configuration** is hashed when it is in `<stage>/etc/`.
- **The event's form** (a fixed struct, re-sent every 1 s) is ICD.md's proposal, used as it is.

## Contracts with the other lanes

- The Launch Manager lane: component `identity_recorder`, type `Reporting`, `--run-dir /tmp/de4sdv-da-bench/run`,
  `MW_COM_CONFIG` = `config/mw_com_config_identity_recorder.json`. The candidate's process and the adapter depend on
  it.
- The manifest (`mw_com_config_identity_recorder.json`): `/de4sdv/driver_assistance/CandidateRecord`, service 7413,
  event `candidate_record` id 1, instance 1, QM, 2 slots, one subscriber, application id 3414. These are the
  warning-contract lane's values (`../score-path/config/README.md`). The probe's manifest is the same with
  application id 3416, which is this lane's proposal.
- The stage (`../score-path/scripts/stage_score_side.py`) lays out what the record reads, including `facts/`.

## Re-deriving a record

```bash
python3 scripts/check_candidate_record.py <run>/score/candidate_record.json \
  --event-sha256 <recordSha256 of the event> --vp-clone <clone holding 014e0e7a> --rehash
```

The script checks the record's own consistency. It then makes a fresh `git clone --shared` at the revision, applies
every recorded difference and checks that the result is not the revision. With `--rehash`, it rehashes each listed
file that is still on the host.

## Tests

```bash
python -m pytest -q implementation/driver-assistance-bench/identity-recorder/tests
VISIONPILOT_CLONE=<clone holding 014e0e7a> python -m pytest -q implementation/driver-assistance-bench/identity-recorder/tests
```

- `test_identity_recorder_units.py` builds the C++ tests with g++ as C++17 and C++20, and runs them. The tests use an
  in-memory file system (`tests/fake_file_system.h`) and fakes for mw::com and the lifecycle client. The SHA-256
  vectors are compared with Python's `hashlib` at test time.
- `test_identity_recorder_record.py` runs the real shell with the POSIX file system and the record writer on a
  synthetic stage on disk (`tests/record_driver.cpp`). It recomputes every digest with `hashlib`, checks the event
  against the file, and runs the re-derivation at the pin with the bench's real patch series.
- `test_identity_recorder_static.py` compiles both mains for syntax against the closed-loop bench's mw::com mock (not
  S-CORE). It compiles the lifecycle client against `../launch-manager/tests/lifecycle_mock`, and checks the ids
  against ICD.md and the other lanes' manifests.

The suite is registered in `tools/run_bench_unit_tests.py`.

## What only the S-CORE host shows (p10-1)

- that the Bazel build compiles and links both binaries against Communication v0.6.0 and Lifecycle v0.10.0;
- that `score_mw_lifecycle_report_running()` succeeds for a `Reporting` component, and that the Launch Manager
  starts the candidate only after it;
- that LoLa delivers the record to a subscriber that subscribes after the first send (the open readiness item of
  phase 8);
- the record's real content: the CUDA libraries the conf names, the bundle's binaries, and the hashing time of about
  2 GB of libraries and networks within the recorder's 60 s ready timeout.
