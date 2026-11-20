"""The S-CORE start's record of the platform and the GPU it ran on (score_platform_record.py), for the evidence record
of each run (RetainedAssistanceRunEvidence: scoreLifecycleVersion, scoreCommunicationVersion,
scoreSOMEIPGatewayCommit and the S-CORE host's GPU in executionEnvironmentIdentity).

The facts are the bundle's own (build_score_bench.sh writes facts/score-mod-explain.txt with Bazel's resolution and
facts/sources.txt with the pinned commits); the fixtures below are those files' real lines, as the S-CORE build of
2026-11-20 wrote them (fake_bundle.FACTS_*). The GPU is nvidia-smi's answer on the S-CORE host. A value the start
cannot read is written as absent with its reason, never empty and never taken from the kit's expectations (pins.sh).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import fake_bundle  # noqa: E402

BENCH = TESTS.parents[1]
SCRIPTS = BENCH / "score-path" / "scripts"
RECORD = SCRIPTS / "score_platform_record.py"
START = SCRIPTS / "start_score_side.sh"
SMI_QUERY = "nvidia-smi --query-gpu=name,driver_version --format=csv,noheader"


def _bundle(tmp: Path, explain: str | None = fake_bundle.FACTS_SCORE_MOD_EXPLAIN,
            sources: str | None = fake_bundle.FACTS_SOURCES) -> Path:
    facts = tmp / "bundle" / "facts"
    facts.mkdir(parents=True)
    if explain is not None:
        (facts / "score-mod-explain.txt").write_text(explain)
    if sources is not None:
        (facts / "sources.txt").write_text(sources)
    return tmp / "bundle"


def _smi(tmp: Path, body: str) -> dict[str, str]:
    """PATH with an nvidia-smi stand-in that answers the query as the L4 does (or as body says)."""
    b = tmp / "bin"
    b.mkdir(exist_ok=True)
    (b / "nvidia-smi").write_text("#!/bin/bash\necho \"$*\" >> \"%s/smi_calls\"\n%s\n" % (tmp, body))
    (b / "nvidia-smi").chmod(0o755)
    return {**os.environ, "PATH": f"{b}:/usr/bin:/bin"}


def _run(bundle: Path, out: Path, env: dict) -> tuple[subprocess.CompletedProcess, dict]:
    p = subprocess.run([sys.executable, str(RECORD), str(bundle), str(out)], capture_output=True, text=True, env=env)
    lines = {}
    for line in p.stdout.splitlines():
        key, _, rest = line.partition(" ")
        if key in ("SCORE_PLATFORM", "SCORE_GPU"):
            lines[key] = json.loads(rest)
    return p, lines


L4_ANSWER = 'echo "NVIDIA L4, 580.178.04"'


def test_the_record_reads_the_platform_pins_from_the_bundles_own_facts(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    p, lines = _run(bundle, tmp_path / "out.json", _smi(tmp_path, L4_ANSWER))
    assert lines.get("SCORE_PLATFORM") == {
        "lifecycle_version": "score_lifecycle@0.10.0", "communication_version": "score_communication@0.6.0",
        "someip_gateway_commit": "d9eac670b7534352749da3d30f52aebf5129f168", "facts": str(bundle / "facts")}, p.stdout
    assert p.returncode == 0, p.stderr


def test_the_record_takes_the_gpu_from_nvidia_smi_on_the_host(tmp_path: Path) -> None:
    p, lines = _run(_bundle(tmp_path), tmp_path / "out.json", _smi(tmp_path, L4_ANSWER))
    assert lines.get("SCORE_GPU") == {"gpus": [{"name": "NVIDIA L4", "driver_version": "580.178.04"}],
                                      "query": SMI_QUERY}, p.stdout
    assert (tmp_path / "smi_calls").read_text().split() == SMI_QUERY.split()[1:]


def test_the_record_writes_both_into_its_json(tmp_path: Path) -> None:
    p, lines = _run(_bundle(tmp_path), tmp_path / "out.json", _smi(tmp_path, L4_ANSWER))
    doc = json.loads((tmp_path / "out.json").read_text()) if (tmp_path / "out.json").exists() else {}
    assert doc == {"score_platform": lines.get("SCORE_PLATFORM"), "score_gpu": lines.get("SCORE_GPU")} and doc, p.stdout


def test_the_platform_values_are_the_bundles_not_the_kits_pins(tmp_path: Path) -> None:
    # another gateway commit and other versions in the bundle's facts: the record names those, never pins.sh's
    other = "e" * 40
    explain = fake_bundle.FACTS_SCORE_MOD_EXPLAIN.replace("score_lifecycle@0.10.0", "score_lifecycle@0.11.0") \
        .replace("score_communication@0.6.0", "score_communication@0.7.1")
    sources = fake_bundle.FACTS_SOURCES.replace("d9eac670b7534352749da3d30f52aebf5129f168", other)
    _, lines = _run(_bundle(tmp_path, explain, sources), tmp_path / "out.json", _smi(tmp_path, L4_ANSWER))
    plat = lines.get("SCORE_PLATFORM", {})
    assert (plat.get("lifecycle_version"), plat.get("communication_version"), plat.get("someip_gateway_commit")) == \
        ("score_lifecycle@0.11.0", "score_communication@0.7.1", other)


@pytest.mark.parametrize("explain, sources, field, needle", [
    (None, fake_bundle.FACTS_SOURCES, "lifecycle_version", "score-mod-explain.txt"),
    (None, fake_bundle.FACTS_SOURCES, "communication_version", "score-mod-explain.txt"),
    (fake_bundle.FACTS_SCORE_MOD_EXPLAIN, None, "someip_gateway_commit", "sources.txt"),
    ("<root> (score_feo@0.0.0)\n", fake_bundle.FACTS_SOURCES, "lifecycle_version", "no score_lifecycle@"),
    (fake_bundle.FACTS_SCORE_MOD_EXPLAIN + "\u2514\u2500\u2500\u2500score_lifecycle@0.9.0 \n", fake_bundle.FACTS_SOURCES,
     "lifecycle_version", "score_lifecycle@0.10.0 and score_lifecycle@0.9.0"),
    (fake_bundle.FACTS_SCORE_MOD_EXPLAIN, "FEO 313b; CARLA 14ac\n", "someip_gateway_commit", "no gateway commit"),
])
def test_a_platform_value_the_facts_do_not_give_is_absent_with_its_reason(tmp_path: Path, explain, sources,
                                                                          field: str, needle: str) -> None:
    p, lines = _run(_bundle(tmp_path, explain, sources), tmp_path / "out.json", _smi(tmp_path, L4_ANSWER))
    value = lines.get("SCORE_PLATFORM", {}).get(field)
    assert isinstance(value, dict) and needle in value.get("absent", ""), (value, p.stdout)
    assert p.returncode == 0


@pytest.mark.parametrize("body, needle", [
    (None, "nvidia-smi not found"),
    ('echo "NVIDIA-SMI has failed because it couldn\'t communicate with the NVIDIA driver."; exit 9',
     "nvidia-smi exit 9: NVIDIA-SMI has failed"),
    ("exit 0", "nvidia-smi listed no GPU"),
])
def test_a_gpu_the_host_does_not_report_is_absent_with_its_reason(tmp_path: Path, body, needle: str) -> None:
    # not found: DA_NVIDIA_SMI names a program that is not there (the default is nvidia-smi on PATH)
    env = _smi(tmp_path, body) if body is not None else {**os.environ, "DA_NVIDIA_SMI": str(tmp_path / "no" / "smi")}
    p, lines = _run(_bundle(tmp_path), tmp_path / "out.json", env)
    gpu = lines.get("SCORE_GPU")
    assert isinstance(gpu, dict) and needle in gpu.get("absent", ""), (gpu, p.stdout)
    assert p.returncode == 0


def test_the_start_prints_the_record_after_its_score_config_line() -> None:
    # the start step's code line (comments dropped): the record runs on the bundle the start staged, after
    # score_config_record.py, and a failure is logged, never the start's failure
    code = [ln for ln in START.read_text().splitlines() if not ln.lstrip().startswith("#")]
    idx = [i for i, ln in enumerate(code) if "score_platform_record.py" in ln]
    cfg = [i for i, ln in enumerate(code) if "score_config_record.py" in ln]
    assert idx and cfg and idx[0] > cfg[0], idx
    assert '"$DA_PYTHON" "$HERE/score_platform_record.py" "$DA_B2_BUNDLE" "$OUT/score_platform.json"' in code[idx[0]]
    assert "|| ss_log" in " ".join(code[idx[0]:idx[0] + 2])


def test_the_fake_bundle_carries_the_facts_in_the_real_format(tmp_path: Path) -> None:
    # the dry runs' bundle has the two facts files the record reads, with the S-CORE build's real lines
    setup = fake_bundle.make_bundle(tmp_path, Path("/bin/true"))
    facts = setup["bundle"] / "facts"
    assert (facts / "score-mod-explain.txt").read_text() == fake_bundle.FACTS_SCORE_MOD_EXPLAIN
    assert (facts / "sources.txt").read_text() == fake_bundle.FACTS_SOURCES
    assert "\u251c\u2500\u2500\u2500score_lifecycle@0.10.0 \n" in fake_bundle.FACTS_SCORE_MOD_EXPLAIN
    assert "; gateway d9eac670b7534352749da3d30f52aebf5129f168; " in fake_bundle.FACTS_SOURCES


@pytest.fixture(scope="module")
def record_driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return fake_bundle.build_record_driver(tmp_path_factory.mktemp("driver"))


def test_a_full_start_prints_the_platform_and_the_gpu_of_its_bundle(tmp_path: Path, record_driver: Path) -> None:
    # the real start_score_side.sh on the fake bundle (its facts in the build's format, the L4's nvidia-smi answer):
    # its output, which the session reads from the step's tail, carries both lines
    setup = fake_bundle.make_bundle(tmp_path, record_driver)
    try:
        p = subprocess.run(["bash", str(START), str(tmp_path / "out"), "10.164.0.2"], capture_output=True, text=True,
                           env=setup["env"], cwd=BENCH, timeout=120)
        tail = p.stdout.splitlines()[-20:]
        got = {ln.split(" ", 1)[0]: json.loads(ln.split(" ", 1)[1]) for ln in tail
               if ln.startswith(("SCORE_PLATFORM ", "SCORE_GPU "))}
        assert got.get("SCORE_PLATFORM", {}).get("lifecycle_version") == "score_lifecycle@0.10.0", p.stdout[-3000:]
        assert got.get("SCORE_GPU") == {"gpus": [{"name": "NVIDIA L4", "driver_version": "580.178.04"}],
                                        "query": SMI_QUERY}
        assert json.loads((tmp_path / "out" / "score_platform.json").read_text())["score_gpu"] == got["SCORE_GPU"]
        assert p.returncode == 0
    finally:
        subprocess.run(["bash", str(SCRIPTS / "stop_score_side.sh"), str(tmp_path / "stop")], env=setup["env"],
                       capture_output=True, cwd=BENCH, timeout=120)
