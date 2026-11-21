"""The session's producers of the evidence record's fields that no other step writes (lane V-b of the S1
integration): session.json configuration_identity, configuration_receipt_sha256, visualization_recorder_delay,
score_platform.{lifecycle_version, communication_version, someip_gateway_commit} and
execution_environment.{score_gpu, sdv_core_image, ivi_image}, the names case-evaluators/evidence_record.py reads
(RetainedAssistanceRunEvidence, driver_assistance_verification_evidence.sysml:174-267).

- The configured product and its receipt come from the committed model at the session's own commit
  (driver_assistance_variability_configuration.sysml: the part DRIVING-CONFIG-002 and the receipt its doc names;
  driver_assistance_verification_evidence.sysml: "It binds DRIVING-CONFIG-002 as its configurationIdentity").
- The recorder's delay is the model's own sentence, verbatim with its source (verification_evidence.sysml:194-200),
  and only for an S-CORE host with the GPU the sentence names.
- The platform pins and the GPU come from each S-CORE start's SCORE_PLATFORM and SCORE_GPU lines, the guest images
  from guest_up's GUEST_IMAGE lines.
A field the session cannot read is {"absent": "<reason>"}, never empty and never guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_guest_images import KEYS as GUEST_KEYS, parse as parse_guest_image
from test_session_dryrun import _vp_env, set_vp_env, vp_clone  # noqa: F401 (the dry runs' fixtures)
from test_session_s1 import LABELS, record, s1_run

HERE = Path(__file__).resolve().parent
SESSION_DIR = HERE.parent
BENCH = SESSION_DIR.parent
REPO = BENCH.parents[1]
sys.path.insert(0, str(SESSION_DIR))
import evidence_fields as ef  # noqa: E402

CONFIG_SYSML = "textual-notation-of-model/packages/features/driving/driver_assistance_variability_configuration.sysml"
EVIDENCE_SYSML = "textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml"
RECEIPT = "model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json"
# the model's sentence of the recorder's delay (verification_evidence.sysml:194-200), as the requirement states it
DELAY = ("the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at "
         "the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4")
DELAY_OPENING = "visualizationRecorderDelay is the delay of the recorder"   # the sentence that holds DELAY
PLATFORM = {"lifecycle_version": "score_lifecycle@0.10.0", "communication_version": "score_communication@0.6.0",
            "someip_gateway_commit": "d9eac670b7534352749da3d30f52aebf5129f168"}
COMMIT = "c" * 40


def disk_reader(overrides: dict | None = None):
    """Reads the repository's files from the disk (a stand-in for `git show <commit>:<path>`), with overrides."""
    def read(path: str) -> bytes:
        if overrides and path in overrides:
            if overrides[path] is None:
                raise ef.NotCommitted(f"{path} is not in commit {COMMIT}")
            return overrides[path]
        return (REPO / path).read_bytes()
    return read


def _text(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def _sentence_lines(text: str, opening: str) -> tuple[int, int]:
    """The first and last line (1-based) of the model's one sentence that begins with `opening`, found in the
    model's text: the doc's words without the ` * ` prefixes, to the sentence's full stop. The pins below follow the
    model so, and the next edit of the model moves them with the sentence."""
    lines = text.splitlines()
    flat, starts = "", []
    for ln in lines:
        starts.append(len(flat))
        flat += re.sub(r"^\s*(/\*+|\*/|\*)\s?", "", ln).strip() + " "
    assert flat.count(opening) == 1, f"the model holds {flat.count(opening)} sentences that begin {opening!r}"
    a = flat.index(opening)
    b = re.compile(r"\.\s").search(flat, a).start()

    def line(pos: int) -> int:
        return max(i for i, s in enumerate(starts) if s <= pos) + 1
    return line(a), line(b)


# ------------------------------------------------------------------------------- the configured product, receipt


def test_the_configuration_is_the_configured_product_the_model_binds() -> None:
    c = ef.configuration(disk_reader(), COMMIT)
    assert c["configuration_identity"] == "DRIVING-CONFIG-002"


def test_the_receipt_sha256_is_that_of_the_committed_receipt_the_configuration_names() -> None:
    c = ef.configuration(disk_reader(), COMMIT)
    assert c["configuration_receipt_sha256"] == hashlib.sha256((REPO / RECEIPT).read_bytes()).hexdigest()
    rec = c["configuration_receipt"]
    assert rec["path"] == RECEIPT and rec["commit"] == COMMIT
    assert rec["model_bound_sha256"] == "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1"
    assert rec["equal_to_model"] is (rec["model_bound_sha256"] == c["configuration_receipt_sha256"])
    # each value names its source, file and line, at the commit
    assert f"{CONFIG_SYSML}:107" in rec["sources"]["configuration_identity"]
    assert f"{CONFIG_SYSML}:138" in rec["sources"]["model_bound_sha256"]
    binds, _ = _sentence_lines(_text(EVIDENCE_SYSML), "It binds DRIVING-CONFIG-002 as its configurationIdentity")
    assert rec["sources"]["evidence_binding"] == f"{EVIDENCE_SYSML}:{binds} at {COMMIT}"


def test_a_receipt_other_than_the_models_bound_one_is_recorded_as_it_is_with_the_difference_named() -> None:
    c = ef.configuration(disk_reader({RECEIPT: b'{"another": "receipt"}\n'}), COMMIT)
    assert c["configuration_receipt_sha256"] == hashlib.sha256(b'{"another": "receipt"}\n').hexdigest()
    assert c["configuration_receipt"]["equal_to_model"] is False


@pytest.mark.parametrize("overrides, field, needle", [
    ({RECEIPT: None}, "configuration_receipt_sha256", "is not in commit"),
    ({CONFIG_SYSML: None}, "configuration_identity", "is not in commit"),
    ({CONFIG_SYSML: None}, "configuration_receipt_sha256", "is not in commit"),
    ({CONFIG_SYSML: _text(CONFIG_SYSML).replace("part <'DRIVING-CONFIG-002'> configuredProduct",
                                                "part configuredProduct").encode()},
     "configuration_identity", "no part <'DRIVING-CONFIG-"),
    ({EVIDENCE_SYSML: _text(EVIDENCE_SYSML).replace("It binds\n     * DRIVING-CONFIG-002 as its",
                                                    "It binds\n     * DRIVING-CONFIG-009 as its").encode()},
     "configuration_identity", "DRIVING-CONFIG-009"),
    ({CONFIG_SYSML: _text(CONFIG_SYSML).replace("receiptSha256 is the SHA-256 of", "receiptSha256 is a digest of")
      .encode()}, "configuration_receipt_sha256", "names no receipt"),
])
def test_a_configuration_value_the_commit_does_not_give_is_absent_with_its_reason(overrides, field: str,
                                                                                  needle: str) -> None:
    v = ef.configuration(disk_reader(overrides), COMMIT)[field]
    assert isinstance(v, dict) and needle in v.get("absent", ""), v


def test_no_commit_gives_absent_configuration_fields() -> None:
    c = ef.configuration(ef.git_reader(REPO, "none"), "none")
    for f in ("configuration_identity", "configuration_receipt_sha256"):
        assert isinstance(c[f], dict) and "no commit" in c[f]["absent"], c[f]


# ------------------------------------------------------------------------------------------- the recorder's delay


def test_the_recorder_delay_is_the_models_sentence_verbatim_with_its_source() -> None:
    d = ef.model_delay(disk_reader(), COMMIT)
    assert d["text"] == DELAY
    assert d["host_gpu"] == "NVIDIA L4"
    first, last = _sentence_lines(_text(EVIDENCE_SYSML), DELAY_OPENING)
    assert d["source"] == f"{EVIDENCE_SYSML}:{first}-{last} at {COMMIT} (RetainedAssistanceRunEvidence)"


def test_the_delay_holds_only_for_the_gpu_the_model_names() -> None:
    d = ef.model_delay(disk_reader(), COMMIT)
    assert ef.recorder_delay(d, "NVIDIA L4, driver 580.178.04", ["NVIDIA L4"]).startswith(DELAY + " (")
    other = ef.recorder_delay(d, "Tesla T4, driver 535.104.05", ["Tesla T4"])
    assert isinstance(other, dict) and "NVIDIA L4" in other["absent"] and "Tesla T4" in other["absent"]
    unread = ef.recorder_delay(d, {"absent": "nvidia-smi not found on the S-CORE host (nvidia-smi)"}, [])
    assert isinstance(unread, dict) and "nvidia-smi not found" in unread["absent"]


def test_a_model_without_the_sentence_gives_an_absent_delay() -> None:
    text = _text(EVIDENCE_SYSML).replace("visualizationRecorderDelay is", "visualizationRecorderDelay was")
    d = ef.model_delay(disk_reader({EVIDENCE_SYSML: text.encode()}), COMMIT)
    assert isinstance(d, dict) and "absent" in d and "visualizationRecorderDelay" in d["absent"]


# ------------------------------------------------------------------------- the S-CORE starts' lines, the guests'


def _platform_line(**over) -> str:
    return "SCORE_PLATFORM " + json.dumps({**PLATFORM, "facts": "/opt/da-b2/bundle/facts", **over})


GPU_LINE = 'SCORE_GPU {"gpus": [{"name": "NVIDIA L4", "driver_version": "580.178.04"}], "query": "nvidia-smi"}'


def _in(tmp: Path, runs: dict, guest: str | None) -> Path:
    (tmp / "score_runs.tsv").write_text("".join(f"{r}\t{k}\t{v}\n" for r, kv in runs.items() for k, v in kv.items()))
    if guest is not None:
        (tmp / "guest_images.txt").write_text(guest)
    (tmp / "evidence_config.json").write_text(json.dumps({**ef.configuration(disk_reader(), COMMIT),
                                                          "model_delay": ef.model_delay(disk_reader(), COMMIT)}))
    return tmp


GUEST = ("GUEST_IMAGE sdv_core serial=0.0.0.0:6521 product=sdv_core_cf build_id=BP4A.1 fingerprint=g/sdv_core_cf/x:17/"
         "BP4A.1/eng.1:eng/test-keys vbmeta_digest=" + "1f" * 32 + "\n"
         "GUEST_IMAGE ivi serial=0.0.0.0:6522 product=sdv_ivi_cf build_id=BP4A.1 fingerprint=g/sdv_ivi_cf/x:17/"
         "BP4A.1/eng.2:eng/test-keys vbmeta_digest=unread\n")


def _fields(tmp: Path, runs: dict, guest: str | None = GUEST, kind: str = "s1") -> tuple[dict, dict]:
    score_runs = {r: dict(kv) for r, kv in runs.items()}
    out = ef.session_fields(str(_in(tmp, runs, guest)), score_runs, kind=kind, guest_host=guest is not None)
    return out, score_runs


def test_the_platform_and_gpu_of_every_start_go_to_the_session_and_to_each_run(tmp_path: Path) -> None:
    runs = {w: {"score_platform": _platform_line()[15:], "score_gpu": GPU_LINE[10:]} for w in ("calib_steer", "a")}
    out, score_runs = _fields(tmp_path, runs)
    assert out["score_platform"] == {**PLATFORM, "facts": "/opt/da-b2/bundle/facts",
                                     "source": "the SCORE_PLATFORM line of every S-CORE start: calib_steer, a"}
    assert out["execution_environment"]["score_gpu"] == "NVIDIA L4, driver 580.178.04"
    assert score_runs["a"]["score_platform"]["lifecycle_version"] == "score_lifecycle@0.10.0"
    assert score_runs["a"]["score_gpu"]["gpus"][0]["name"] == "NVIDIA L4"
    assert out["visualization_recorder_delay"].startswith(DELAY + " (")
    assert out["configuration_identity"] == "DRIVING-CONFIG-002"


def test_starts_that_disagree_give_an_absent_session_value_naming_each_run(tmp_path: Path) -> None:
    runs = {"a": {"score_platform": _platform_line()[15:], "score_gpu": GPU_LINE[10:]},
            "b": {"score_platform": _platform_line(lifecycle_version="score_lifecycle@0.11.0")[15:],
                  "score_gpu": GPU_LINE[10:].replace("580.178.04", "570.1")}}
    out, _ = _fields(tmp_path, runs)
    lv = out["score_platform"]["lifecycle_version"]
    assert isinstance(lv, dict) and "a: score_lifecycle@0.10.0" in lv["absent"] and "b: score_lifecycle@0.11.0" in \
        lv["absent"]
    assert out["score_platform"]["communication_version"] == "score_communication@0.6.0"
    gpu = out["execution_environment"]["score_gpu"]
    assert isinstance(gpu, dict) and "570.1" in gpu["absent"]
    assert isinstance(out["visualization_recorder_delay"], dict)


def test_a_start_that_printed_no_line_is_named_in_the_absent_reason(tmp_path: Path) -> None:
    # "staged": the start ran (score_config_check records it for every start), but printed no SCORE_PLATFORM line
    runs = {"a": {"score_platform": _platform_line()[15:], "score_gpu": GPU_LINE[10:]}, "b": {"setting": "x",
                                                                                               "staged": ""}}
    out, score_runs = _fields(tmp_path, runs)
    lv = out["score_platform"]["lifecycle_version"]
    assert isinstance(lv, dict) and "b" in lv["absent"] and "no SCORE_PLATFORM line" in lv["absent"]
    assert isinstance(score_runs["b"]["score_platform"], dict) and "absent" in score_runs["b"]["score_platform"]


def test_a_run_whose_start_never_ran_gives_no_vote(tmp_path: Path) -> None:
    # an owed run (the session ended before its S-CORE start): absent in its own entry, and the session's value is
    # that of the starts that ran
    runs = {"a": {"score_platform": _platform_line()[15:], "score_gpu": GPU_LINE[10:]}, "b": {"setting": "x"}}
    out, score_runs = _fields(tmp_path, runs)
    assert out["score_platform"]["lifecycle_version"] == "score_lifecycle@0.10.0"
    assert out["execution_environment"]["score_gpu"] == "NVIDIA L4, driver 580.178.04"
    assert "did not run" in score_runs["b"]["score_platform"]["absent"]


def test_no_start_at_all_gives_absent_platform_and_gpu(tmp_path: Path) -> None:
    out, _ = _fields(tmp_path, {}, kind="p10-3")
    for v in (out["score_platform"]["lifecycle_version"], out["execution_environment"]["score_gpu"]):
        assert isinstance(v, dict) and "no S-CORE start" in v["absent"]


def test_the_guest_images_are_read_from_guest_ups_lines(tmp_path: Path) -> None:
    out, _ = _fields(tmp_path, {})
    ee = out["execution_environment"]
    assert ee["sdv_core_image"] == ("sdv_core_cf, build BP4A.1, fingerprint g/sdv_core_cf/x:17/BP4A.1/eng.1:eng/"
                                    "test-keys, vbmeta digest " + "1f" * 32)
    assert ee["ivi_image"] == ("sdv_ivi_cf, build BP4A.1, fingerprint g/sdv_ivi_cf/x:17/BP4A.1/eng.2:eng/test-keys, "
                               "vbmeta digest unread")


def test_guest_images_absent_without_the_guest_host_or_without_a_fingerprint(tmp_path: Path) -> None:
    out, _ = _fields(tmp_path, {}, guest=None)
    for k in ("sdv_core_image", "ivi_image"):
        assert "without the guest host" in out["execution_environment"][k]["absent"]
    (tmp_path / "x").mkdir()
    out, _ = _fields(tmp_path / "x", {}, guest=GUEST.replace(
        "fingerprint=g/sdv_ivi_cf/x:17/BP4A.1/eng.2:eng/test-keys", "fingerprint=unread"))
    assert "fingerprint" in out["execution_environment"]["ivi_image"]["absent"]
    (tmp_path / "y").mkdir()
    out, _ = _fields(tmp_path / "y", {}, guest="")
    assert "no GUEST_IMAGE line" in out["execution_environment"]["sdv_core_image"]["absent"]


def test_no_preflight_record_gives_absent_configuration_and_delay(tmp_path: Path) -> None:
    out = ef.session_fields(str(tmp_path), {}, kind="s1", guest_host=False)
    for f in ("configuration_identity", "configuration_receipt_sha256", "visualization_recorder_delay"):
        assert isinstance(out[f], dict) and "evidence_config.json" in out[f]["absent"], out[f]


# ------------------------------------------------------------------------------------------- dry runs of the session


@pytest.fixture(scope="module")
def s1_default(tmp_path_factory, vp_clone) -> tuple:
    tmp = tmp_path_factory.mktemp("s1ev")
    # module scope starts before the function-scoped autouse _vp_env: the stand-in clone is set here, or the session
    # would read the host's own VisionPilot clone (the test VM and the GCC 13 image have none)
    with pytest.MonkeyPatch.context() as mp:
        set_vp_env(vp_clone, mp)
        r = s1_run(tmp, "--owner-ok-guest-host", "--permissive-ivi", "--camcal", "settings")
    return r, record(r)


def _committed(path: str) -> bytes | None:
    if shutil.which("git") is None:
        return None
    p = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{path}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


def test_an_s1_session_records_the_configuration_of_its_own_commit(s1_default) -> None:
    r, rec = s1_default
    assert r.rc == 0, r.log[-3000:]
    receipt = _committed(RECEIPT)
    if receipt is None:   # a tree without git (the GCC 13 gate image): absent with the reason, never a value
        assert "commit" in rec["configuration_identity"]["absent"], rec["configuration_identity"]
        return
    assert rec["configuration_identity"] == "DRIVING-CONFIG-002"
    assert rec["configuration_receipt_sha256"] == hashlib.sha256(receipt).hexdigest()
    assert rec["configuration_receipt"]["commit"] == rec["bench_commit"]
    assert "configuration DRIVING-CONFIG-002, receipt sha256 " in r.log


def test_an_s1_session_records_each_starts_platform_and_gpu(s1_default) -> None:
    r, rec = s1_default
    for w in ["calib_steer", *LABELS]:
        assert {k: rec["score_runs"][w]["score_platform"][k] for k in PLATFORM} == PLATFORM, w
        assert rec["score_runs"][w]["score_gpu"]["gpus"] == [{"name": "NVIDIA L4", "driver_version": "580.178.04"}]
    assert {k: rec["score_platform"][k] for k in PLATFORM} == PLATFORM
    assert rec["execution_environment"]["score_gpu"] == "NVIDIA L4, driver 580.178.04"
    committed = _committed(EVIDENCE_SYSML)
    if committed is None:   # a tree without git (the GCC 13 gate image): absent with the reason
        assert "commit" in rec["visualization_recorder_delay"]["absent"], rec["visualization_recorder_delay"]
    else:   # the session read the model at its commit: the sentence's lines there
        first, last = _sentence_lines(committed.decode("utf-8"), DELAY_OPENING)
        assert rec["visualization_recorder_delay"].startswith(f"{DELAY} ({EVIDENCE_SYSML}:{first}-{last} at ")
    assert "S-CORE platform of 012_20_r1: score_lifecycle@0.10.0, score_communication@0.6.0, gateway d9eac670" in r.log


def test_an_s1_session_records_the_guest_images_guest_up_printed(s1_default) -> None:
    r, rec = s1_default
    ee = rec["execution_environment"]
    assert ee["sdv_core_image"].startswith("sdv_core_cf, build ") and ee["ivi_image"].startswith("sdv_ivi_cf, build ")
    lines = (r.incoming / "guest_images.txt").read_text().splitlines()
    # the fake's lines have guest_up's own shape (test_guest_images.py pins guest_up's)
    assert [parse_guest_image(ln)[:2] for ln in lines] == [("sdv_core", list(GUEST_KEYS)), ("ivi", list(GUEST_KEYS))]


def test_the_evidence_record_finds_none_of_these_attributes_empty(s1_default) -> None:
    # lane I-E's reader (case-evaluators/evidence_record.py) on the session tree: the attributes this lane feeds are
    # filled in the record of every run, the stop run included
    r, rec = s1_default
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import runio_da, evidence_record as er; "
            "s = runio_da.discover(sys.argv[2]); print(json.dumps({k: v['emptyAttributes'] for k, v in "
            "er.build_all(s).items()}))")
    p = subprocess.run([sys.executable, "-c", code, str(BENCH / "case-evaluators"), str(r.incoming)],
                       capture_output=True, text=True)
    empty = json.loads(p.stdout) if p.returncode == 0 else {}
    assert sorted(empty) == sorted(LABELS), p.stderr[-2000:]
    ours = {"scoreLifecycleVersion", "scoreCommunicationVersion", "scoreSOMEIPGatewayCommit",
            "executionEnvironmentIdentity"} | \
        ({"configurationIdentity", "receiptSha256", "visualizationRecorderDelay"}   # read from the session's commit
         if _committed(RECEIPT) is not None else set())
    assert {w: sorted(ours & set(e)) for w, e in empty.items()} == {w: [] for w in LABELS}


def test_a_gpu_other_than_the_models_and_no_guest_host_give_absent_fields(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", FAKE_SCORE_GPU="Tesla T4, 535.104.05")
    rec = record(r)
    assert r.rc == 0, r.log[-3000:]
    assert rec["execution_environment"]["score_gpu"] == "Tesla T4, driver 535.104.05"
    d = rec["visualization_recorder_delay"]
    if _committed(EVIDENCE_SYSML) is None:   # a tree without git (the GCC 13 gate image): absent for the commit
        assert isinstance(d, dict) and "commit" in d["absent"], d
    else:
        assert isinstance(d, dict) and "NVIDIA L4" in d["absent"] and "Tesla T4" in d["absent"]
    for k in ("sdv_core_image", "ivi_image"):
        assert "without the guest host" in rec["execution_environment"][k]["absent"]
