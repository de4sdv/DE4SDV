"""The second VisionPilot candidate of decision D4 (INC-DRIVING-002): the pin 014e0e7a plus DE4SDV's port of the two
fixes of upstream draft PR #427, as an optional fourth patch of the bench's series.

- The build selects the series by DA_CANDIDATE: pin (the default) is the patches of patches/ (0001-0003 and 0005, the
  warm start of D-S1-1), pr427 is those and 0004, applied in file-name order (0004 before 0005).
- 0004 applies cleanly on 0001-0003 at the pin (check_patch.sh on a scratch clone), and `git diff` re-creates its body.
- The variant's facts/ list 0004: the source difference that the staging copies and the identity recorder hashes.
- With the default, the bundle step's contract is the one of the base commit, path for path and source for source;
  the check and the build apply series.sh's list in order.
- The variant bundle has its own root and archive name, so it can never be taken for the pin's.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from test_score_build import BUILD_DIR, BENCH, PATCHES, SERIES, bundle_step_outputs, have_clone, CLONE

SERIES_SH = BENCH / "score-interface" / "series.sh"
CHECK = BENCH / "score-interface" / "check_patch.sh"
BUILD = BUILD_DIR / "build_score_bench.sh"
CANDIDATE = BENCH / "score-interface" / "candidates" / "pr427"
P0004 = "0004-de4sdv-port-of-upstream-pr427.diff"
BASE = "1bfbd6b4"  # the commit this lane started from: the default's contract there is the reference


def run(args: list[str], candidate: str | None = None, **kw) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON") and k != "DA_CANDIDATE"}
    if candidate is not None:
        env["DA_CANDIDATE"] = candidate
    return subprocess.run(args, capture_output=True, text=True, env=env, **kw)


def series(candidate: str | None) -> list[str]:
    out = run(["bash", str(SERIES_SH), "list"], candidate)
    assert out.returncode == 0, out.stderr
    return [Path(line).name for line in out.stdout.split()]


def test_the_default_selects_the_pins_series() -> None:
    assert series(None) == SERIES
    assert series("pin") == SERIES


def test_the_variant_selects_0004_before_0005() -> None:
    assert series("pr427") == SERIES[:3] + [P0004] + SERIES[3:]
    paths = run(["bash", str(SERIES_SH), "list"], "pr427").stdout.split()
    assert Path(paths[3]) == CANDIDATE / P0004
    names = SERIES[:3] + [None] + SERIES[3:]
    assert all(Path(p) == PATCHES / n for p, n in zip(paths, names) if n is not None)


def test_an_unknown_candidate_is_refused() -> None:
    out = run(["bash", str(SERIES_SH), "list"], "main")
    assert out.returncode != 0
    assert "unknown candidate" in out.stderr


def test_0004_is_listed_in_the_candidates_sums_and_names_its_origin() -> None:
    sums = (CANDIDATE / "SHA256SUMS").read_text().split()
    assert sums == [hashlib.sha256((CANDIDATE / P0004).read_bytes()).hexdigest(), P0004]
    head = (CANDIDATE / P0004).read_text().split("\ndiff --git ", 1)[0]
    for needle in ("PR #427", "a38f227c", "f06f84eb", "014e0e7a", "not upstream's commit",
                   "VisionPilot/app/vision_pilot.cpp:177-179", "longitudinal_planning.cpp:17",
                   "longitudinal_fusion.cpp:146-155", "fusion.ad_only_needs_as_track"):
        assert needle in head, needle


def facts(candidate: str, dest: Path) -> dict[str, bytes]:
    out = run(["bash", str(SERIES_SH), "facts", str(dest)], candidate)
    assert out.returncode == 0, out.stderr
    return {p.name: p.read_bytes() for p in sorted(dest.iterdir())}


def test_the_default_facts_are_the_patches_dir_byte_for_byte(tmp_path: Path) -> None:
    got = facts("pin", tmp_path)
    want = {p.name: p.read_bytes() for p in sorted(PATCHES.iterdir()) if p.name == "SHA256SUMS" or p.suffix == ".diff"}
    assert got == want


def test_the_variants_facts_list_0004(tmp_path: Path) -> None:
    got = facts("pr427", tmp_path)
    assert sorted(got) == sorted(SERIES + [P0004, "SHA256SUMS"])
    lines = got["SHA256SUMS"].decode().splitlines()
    pin = (PATCHES / "SHA256SUMS").read_text().splitlines()
    assert lines[:len(pin)] == pin
    assert lines[len(pin):] == [f"{hashlib.sha256(got[P0004]).hexdigest()}  {P0004}"]
    assert subprocess.run(["sha256sum", "-c", "--quiet", "SHA256SUMS"], cwd=tmp_path).returncode == 0
    # every diff the staging would copy is listed (identity recorder's input rule)
    assert {line.split()[1] for line in lines} == {n for n in got if n.endswith(".diff")}


def base_build_script() -> str:
    return subprocess.run(["git", "-C", str(BENCH), "show", f"{BASE}:implementation/driver-assistance-bench/"
                           "score-build/build_score_bench.sh"], check=True, capture_output=True, text=True).stdout


def test_the_default_bundle_contract_is_unchanged() -> None:
    """Every path the bundle step writes, and where it comes from, is the base commit's (the variant's extra facts go
    through series.sh, behind the candidate guard). The stages' facts directory is $FACTS, which is $ROOT/facts for
    the pin (test_the_default_layout_is_the_pins)."""
    head = BUILD.read_text().replace('"$FACTS"/', '"$ROOT"/facts/').replace('"$FACTS/', '"$ROOT/facts/')
    # the additions since: the stop run's control client and its mw::com configuration (C4 of the S1 build), and the
    # visualization recorder's encode check (lane V-a of the S1 integration; never staged)
    added = {"bin/lm_control_client": "$SB/de4sdv_da_bench/launch-manager/lm_control_client",
             "bin/visualization_recorder_check": "$SB/de4sdv_da_bench/score-build/workspace/visualization_recorder_check",
             "config/launch_manager/mw_com_config_lm_control_client.json":
                 "$BENCH/launch-manager/config/mw_com_config_lm_control_client.json"}
    produced, pairs, whole = bundle_step_outputs(head)
    base_produced, base_pairs, base_whole = bundle_step_outputs(base_build_script())
    assert produced == base_produced | set(added)
    assert [p for p in pairs if p[0] not in added] == base_pairs
    assert sorted(p for p in pairs if p[0] in added) == sorted(added.items())
    assert whole == base_whole
    bundle = BUILD.read_text().split("\nstep bundle\n", 1)[1]
    extra = [line.strip() for line in bundle.splitlines() if "series.sh" in line]
    assert extra == ['[ "$DA_CANDIDATE" = pin ] || "$BENCH/score-interface/series.sh" facts "$B/facts"']


def test_the_build_applies_the_candidates_list_in_order() -> None:
    """The base commit applied 0001-0003 by name and the candidate's extras after them; the head applies series.sh's
    list, which for the pin is those three and 0005, and for pr427 puts 0004 before 0005."""
    def applied(text: str) -> list[str]:
        return re.findall(r'git -C "\$VP" apply --index "\$BENCH/score-interface/patches/([^"]+)"', text)
    assert applied(base_build_script()) == SERIES[:3]
    assert applied(BUILD.read_text()) == []
    stage = BUILD.read_text().split("\nstep visionpilot\n", 1)[1].split("\nstep workspace\n", 1)[0]
    extra = [line.strip() for line in stage.splitlines() if "series.sh" in line]
    assert extra == ['for p in $("$BENCH/score-interface/series.sh" list); do']


def layout(candidate: str | None, root: str = "/opt/da-b2") -> dict[str, str]:
    out = run(["bash", str(BUILD), "--root", root, "--print-layout"], candidate)
    assert out.returncode == 0, out.stderr
    return dict(item.split("=", 1) for item in out.stdout.split())


def test_the_default_layout_is_the_pins() -> None:
    assert layout(None) == layout("pin") == {
        "candidate": "pin", "root": "/opt/da-b2", "vp": "/opt/da-b2/src/vp", "mark": "visionpilot",
        "facts": "/opt/da-b2/facts", "logs": "/opt/da-b2/logs",
        "bundle": "/opt/da-b2/bundle", "archive": "/opt/da-b2/da-b2-bundle.tgz"}


def test_the_variant_bundle_has_its_own_root() -> None:
    v = layout("pr427")
    assert v == {"candidate": "pr427", "root": "/opt/da-b2", "vp": "/opt/da-b2/src/vp-pr427",
                 "mark": "visionpilot-pr427", "facts": "/opt/da-b2-pr427/facts", "logs": "/opt/da-b2-pr427/logs",
                 "bundle": "/opt/da-b2-pr427/bundle",
                 "archive": "/opt/da-b2-pr427/da-b2-pr427-bundle.tgz"}
    pin = layout("pin")
    for key in ("vp", "facts", "logs", "bundle", "archive"):
        assert not v[key].startswith(pin["bundle"]) and v[key] != pin[key], key


def test_the_build_refuses_an_unknown_candidate() -> None:
    out = run(["bash", str(BUILD), "--root", "/opt/da-b2", "--print-layout"], "main")
    assert out.returncode != 0
    assert "unknown candidate" in (out.stdout + out.stderr)


needs_clone = pytest.mark.skipif(not have_clone() or shutil.which("git") is None,
                                 reason=f"no VisionPilot clone with the pin at {CLONE} (VISIONPILOT_CLONE)")


@needs_clone
def test_0004_applies_cleanly_on_the_series_at_the_pin(tmp_path: Path) -> None:
    out = run(["bash", str(CHECK), str(CLONE), str(tmp_path / "check")], "pr427")
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-2000:]
    assert f"{P0004[:4]} git apply --check on top of 0003: ok" in out.stdout
    assert "git diff against 0003 re-creates 0004's body byte for byte" in out.stdout
    # 0005 (the warm start) after it: the same hunks as on the pin's series, only its index lines differ
    assert "0005 git apply --check on top of 0004: ok" in out.stdout
    assert ("git diff against 0004 re-creates 0005's body byte for byte but its index lines (made on the pin's "
            "series)") in out.stdout
    assert out.stdout.rstrip().endswith("=== check_patch: PASS")


@needs_clone
def test_the_default_check_applies_no_0004(tmp_path: Path) -> None:
    out = run(["bash", str(CHECK), str(CLONE), str(tmp_path / "check")], None)
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-2000:]
    assert "0004" not in out.stdout
    assert "git diff against 0003 re-creates 0005's body byte for byte\n" in out.stdout
    assert out.stdout.rstrip().endswith("=== check_patch: PASS")
